# -*- coding: utf-8 -*-

import json
from datetime import datetime

from odoo import api, fields, models
from odoo.tools import html_escape


class PosPaymentXenditTransaction(models.Model):
    _name = "pos.payment.xendit.transaction"
    _description = "POS Payment Xendit Transaction"
    _order = "id desc"

    name = fields.Char(
        string="Transaction Number",
        required=True,
        readonly=True,
        copy=False,
        default="New",
    )
    payment_request_id = fields.Char(string="Payment Request ID", readonly=True, index=True)
    reference_id = fields.Char(string="Reference ID", readonly=True)
    pos_order_uid = fields.Char(string="POS Order UID", readonly=True, index=True)
    pos_reference = fields.Char(string="POS Reference", readonly=True, index=True)
    pos_payment_method_id = fields.Many2one(
        "pos.payment.method",
        string="POS Payment Method",
        readonly=True,
        ondelete="set null",
    )
    pos_payment_line_cid = fields.Char(string="POS Payment Line CID", readonly=True)
    cashier_name = fields.Char(string="Cashier Name", readonly=True)
    cashier_id = fields.Integer(string="Cashier ID", readonly=True)
    cashier_type = fields.Char(string="Cashier Type", readonly=True)
    session_user_id = fields.Integer(string="Session User ID", readonly=True)
    session_user_name = fields.Char(string="Session User Name", readonly=True)
    xendit_config_id = fields.Many2one(
        "pos.payment.xendit.config",
        string="Xendit Config",
        readonly=True,
        ondelete="restrict",
    )
    webhook_id = fields.Many2one(
        "pos.payment.xendit.webhook",
        string="Webhook Log",
        readonly=True,
        ondelete="set null",
    )
    currency = fields.Char(string="Currency", readonly=True)
    request_amount = fields.Float(string="Request Amount", readonly=True)
    channel_code = fields.Char(string="Channel Code", readonly=True)
    xendit_status = fields.Char(string="Xendit Status", readonly=True)
    payment_date = fields.Datetime(string="Payment Date", readonly=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("pending", "Waiting Payment"),
            ("paid", "Paid"),
            ("failed", "Failed"),
            ("expired", "Expired"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        readonly=True,
        default="draft",
    )
    expires_at = fields.Datetime(string="Expires At", readonly=True)
    qr_data = fields.Text(string="Qr Data", readonly=True)
    order_line_payload = fields.Text(string="Order Line Payload", readonly=True)
    order_line_html = fields.Html(string="Order Lines", readonly=True, sanitize=False)

    @api.model
    def create(self, vals):
        if vals.get("name", "New") == "New":
            vals["name"] = self.env["ir.sequence"].next_by_code("pos.payment.xendit.transaction") or "New"
        return super(PosPaymentXenditTransaction, self).create(vals)

    @api.model
    def _map_xendit_status_to_state(self, xendit_status):
        status_map = {
            "REQUIRES_ACTION": "pending",
            "PENDING": "pending",
            "SUCCEEDED": "paid",
            "PAID": "paid",
            "FAILED": "failed",
            "EXPIRED": "expired",
            "CANCELLED": "cancelled",
        }
        return status_map.get((xendit_status or "").upper(), "draft")

    @api.model
    def _get_state_label(self, state):
        return dict(self._fields["state"].selection).get(state, state or False)

    @api.model
    def _parse_xendit_datetime(self, value):
        if not value:
            return False

        normalized_value = value.replace("Z", "+00:00")
        try:
            parsed_value = datetime.fromisoformat(normalized_value)
        except ValueError:
            return False
        return fields.Datetime.to_string(parsed_value)

    @api.model
    def _extract_transaction_payload(self, response_payload):
        if not isinstance(response_payload, dict):
            return {}

        nested_payload = response_payload.get("data")
        if isinstance(nested_payload, dict) and nested_payload.get("payment_request_id"):
            return nested_payload
        return response_payload

    @api.model
    def _normalize_order_lines(self, order_lines):
        normalized_lines = []
        for line in order_lines or []:
            if not isinstance(line, dict):
                continue

            product_name = line.get("product_name") or line.get("name") or "-"
            try:
                qty = float(line.get("qty") or 0.0)
            except (TypeError, ValueError):
                qty = 0.0

            normalized_lines.append({
                "product_id": line.get("product_id"),
                "product_name": product_name,
                "qty": qty,
            })

        return normalized_lines

    @api.model
    def _build_order_lines_html(self, order_lines):
        order_lines = self._normalize_order_lines(order_lines)
        if not order_lines:
            return False

        rows = []
        for line in order_lines:
            rows.append(
                """
                <tr>
                    <td style="padding: 6px 8px; border: 1px solid #d8dadd;">%s</td>
                    <td style="padding: 6px 8px; border: 1px solid #d8dadd; text-align: right;">%s</td>
                </tr>
                """
                % (html_escape(line["product_name"]), html_escape("%s" % line["qty"]))
            )

        return """
            <table style="width: 100%%; border-collapse: collapse;">
                <thead>
                    <tr>
                        <th style="padding: 6px 8px; border: 1px solid #d8dadd; text-align: left;">Product</th>
                        <th style="padding: 6px 8px; border: 1px solid #d8dadd; text-align: right;">Qty</th>
                    </tr>
                </thead>
                <tbody>%s</tbody>
            </table>
        """ % "".join(rows)

    @api.model
    def _to_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return False

    @api.model
    def create_from_qris_response(self, xendit_config, response_payload, pos_payload=None):
        if not xendit_config or not isinstance(response_payload, dict):
            return False

        pos_payload = pos_payload or {}
        transaction_payload = self._extract_transaction_payload(response_payload)
        if not transaction_payload:
            return False

        actions = transaction_payload.get("actions") or []
        payment_request_id = transaction_payload.get("payment_request_id")
        if not payment_request_id:
            return False

        payment_method_id = self._to_int(pos_payload.get("payment_method_id"))
        order_lines = self._normalize_order_lines(pos_payload.get("order_lines"))

        vals = {
            "payment_request_id": payment_request_id,
            "reference_id": transaction_payload.get("reference_id"),
            "pos_order_uid": pos_payload.get("pos_order_uid"),
            "pos_reference": pos_payload.get("pos_reference"),
            "pos_payment_method_id": payment_method_id,
            "pos_payment_line_cid": pos_payload.get("payment_line_cid"),
            "cashier_name": pos_payload.get("cashier_name"),
            "cashier_id": self._to_int(pos_payload.get("cashier_id")),
            "cashier_type": pos_payload.get("cashier_type"),
            "session_user_id": self._to_int(pos_payload.get("session_user_id")),
            "session_user_name": pos_payload.get("session_user_name"),
            "xendit_config_id": xendit_config.id,
            "currency": transaction_payload.get("currency"),
            "request_amount": transaction_payload.get("request_amount") or 0.0,
            "channel_code": transaction_payload.get("channel_code"),
            "xendit_status": transaction_payload.get("status"),
            "state": self._map_xendit_status_to_state(transaction_payload.get("status")),
            "order_line_payload": json.dumps(order_lines, indent=2) if order_lines else False,
            "order_line_html": self._build_order_lines_html(order_lines),
        }
        if "channel_properties" in transaction_payload:
            vals["expires_at"] = self._parse_xendit_datetime(
                (transaction_payload.get("channel_properties") or {}).get("expires_at")
            )
        if actions:
            vals["qr_data"] = json.dumps(actions, indent=2)

        if payment_request_id:
            transaction = self.sudo().search([("payment_request_id", "=", payment_request_id)], limit=1)
            if transaction:
                transaction.write(vals)
                return transaction

        return self.sudo().create(vals)

    @api.model
    def update_status_from_webhook(self, xendit_config, response_payload, webhook=False):
        if not xendit_config or not isinstance(response_payload, dict):
            return False

        transaction_payload = self._extract_transaction_payload(response_payload)
        payment_request_id = transaction_payload.get("payment_request_id")
        if not payment_request_id:
            return False

        transaction = self.sudo().search(
            [
                ("payment_request_id", "=", payment_request_id),
                ("xendit_config_id", "=", xendit_config.id),
            ],
            limit=1,
        )
        if not transaction:
            return False

        vals = {
            "xendit_status": transaction_payload.get("status"),
            "state": self._map_xendit_status_to_state(transaction_payload.get("status")),
        }
        if webhook:
            vals["webhook_id"] = webhook.id
            vals["payment_date"] = webhook.received_at

        transaction.write(vals)
        return transaction

    @api.model
    def cancel_from_pos(self, xendit_config, transaction_id=None, payment_request_id=None):
        if not xendit_config:
            return {
                "found": False,
                "cancelled": False,
                "state": "draft",
                "xendit_status": False,
            }

        domain = [("xendit_config_id", "=", xendit_config.id)]
        if transaction_id:
            domain.append(("id", "=", self._to_int(transaction_id)))
        elif payment_request_id:
            domain.append(("payment_request_id", "=", payment_request_id))
        else:
            return {
                "found": False,
                "cancelled": False,
                "state": "draft",
                "xendit_status": False,
            }

        transaction = self.sudo().search(domain, limit=1)
        if not transaction:
            return {
                "found": False,
                "cancelled": False,
                "state": "draft",
                "xendit_status": False,
            }

        if transaction.state == "paid":
            return {
                "found": True,
                "cancelled": False,
                "transaction_id": transaction.id,
                "payment_request_id": transaction.payment_request_id,
                "state": transaction.state,
                "xendit_status": transaction.xendit_status,
            }

        if transaction.state != "cancelled":
            transaction.write({
                "xendit_status": "CANCELLED",
                "state": "cancelled",
            })

        return {
            "found": True,
            "cancelled": True,
            "transaction_id": transaction.id,
            "payment_request_id": transaction.payment_request_id,
            "state": transaction.state,
            "xendit_status": transaction.xendit_status,
        }
