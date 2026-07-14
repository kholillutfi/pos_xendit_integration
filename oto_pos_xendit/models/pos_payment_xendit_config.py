# -*- coding: utf-8 -*-

import base64
import io
import json
import logging

import qrcode
import requests

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)


class PosPaymentXenditConfig(models.Model):
    _name = "pos.payment.xendit.config"
    _description = "Pos Payment Xendit Configuration"
    _order = "name"

    name = fields.Char(required=True)
    secret_key = fields.Char(string="Secret Key", required=True, copy=False)
    webhook_token = fields.Char(string="Webhook Token", copy=False)
    api_base_url = fields.Char(
        string="QRIS Request URL",
        required=True,
    )
    payment_api_base_url = fields.Char(
        string="Test Payment URL",
    )
    api_version = fields.Char(
        string="API Version",
        required=True,
    )
    environment = fields.Selection(
        selection=[
            ("test", "Test"),
            ("live", "Production"),
        ],
        required=True,
        default="test",
    )
    body = fields.Text(
        "Body Parameter",
        default="""{
            "description": "Test QRIS",
            "reference_id": "POS-ORDER-TEST-001",
            "type": "PAY",
            "country": "ID",
            "currency": "IDR",
            "request_amount": 1000,
            "capture_method": "AUTOMATIC",
            "channel_code": "QRIS"}
        """,
    )
    payment_body = fields.Text(
        "Payment Body Parameter",
        default="""{
            "payment_request_id": "PAYMENT-REQUEST-TEST-001"
        }""",
    )
    response = fields.Text("Response", readonly=True)
    payment_response = fields.Text("Payment Response", readonly=True)
    qris_image = fields.Binary("QRIS Image", readonly=True, copy=False, attachment=False)

    def action_request_qris(self, pos_payload=None):
        self.ensure_one()
        config = self.sudo() if pos_payload else self
        config.write({"payment_response": False})
        request_body = config._prepare_pos_qris_body(pos_payload) if pos_payload else config.body
        return config.action_request_api(
            config.api_base_url,
            request_body,
            response_field="response",
            generate_qris_image=True,
            body_label=_("QRIS Body"),
            create_transaction=True,
            transaction_context=pos_payload,
            return_payload=bool(pos_payload),
        )

    def action_test_payment(self):
        self.ensure_one()
        return self.action_request_api(
            self.payment_api_base_url,
            self.payment_body,
            response_field="payment_response",
            body_label=_("Payment Body"),
        )

    def _generate_qris_image_from_response(self, response_payload):
        self.ensure_one()
        if not isinstance(response_payload, dict):
            return False

        qr_string = self._extract_qris_string_from_response(response_payload)
        if qr_string:
            # QR string dari Xendit diubah menjadi PNG agar bisa langsung dilihat di form Odoo.
            image_buffer = io.BytesIO()
            qrcode.make(qr_string).save(image_buffer, format="PNG")
            return base64.b64encode(image_buffer.getvalue())

        return False

    def _extract_qris_string_from_response(self, response_payload):
        self.ensure_one()
        if not isinstance(response_payload, dict):
            return False

        transaction_payload = self.env["pos.payment.xendit.transaction"]._extract_transaction_payload(response_payload)
        for action in transaction_payload.get("actions", []):
            if action.get("descriptor") == "QR_STRING" and action.get("value"):
                return action["value"]
        return False

    def _create_xendit_transaction_from_response(self, response_payload, transaction_context=None):
        self.ensure_one()
        return self.env["pos.payment.xendit.transaction"].create_from_qris_response(
            self,
            response_payload,
            pos_payload=transaction_context,
        )

    def _load_request_body(self, request_body, body_label=None):
        if isinstance(request_body, dict):
            return dict(request_body)

        try:
            body = json.loads(request_body or "{}")
        except ValueError as error:
            raise ValidationError(_("%s harus berupa JSON valid.\nDetail: %s") % (body_label or _("Body Parameter"), error))

        if not isinstance(body, dict):
            raise ValidationError(_("%s harus berupa JSON object.") % (body_label or _("Body Parameter")))

        return body

    def _prepare_pos_qris_body(self, pos_payload):
        self.ensure_one()
        pos_payload = pos_payload or {}
        body = self._load_request_body(self.body, _("QRIS Body"))

        try:
            amount = float(pos_payload.get("amount") or body.get("request_amount") or 0.0)
        except (TypeError, ValueError):
            amount = 0.0
        if amount <= 0:
            raise ValidationError(_("Nominal QRIS dari POS harus lebih besar dari 0."))

        xendit_reference = (
            pos_payload.get("pos_order_uid")
            or pos_payload.get("pos_reference")
            or body.get("reference_id")
        )
        if not xendit_reference:
            raise ValidationError(_("POS reference harus dikirim dari POS."))

        body.update({
            "reference_id": xendit_reference,
            "request_amount": int(round(amount)),
        })
        body.setdefault("description", _("POS QRIS %s") % xendit_reference)
        body.setdefault("type", "PAY")
        body.setdefault("country", "ID")
        body.setdefault("currency", "IDR")
        body.setdefault("capture_method", "AUTOMATIC")
        body.setdefault("channel_code", "QRIS")
        return body

    def _prepare_pos_qris_response(self, api_response, response_payload, qris_image, transaction):
        self.ensure_one()
        transaction_model = self.env["pos.payment.xendit.transaction"]
        transaction_payload = transaction_model._extract_transaction_payload(response_payload)
        qris_image_text = qris_image.decode("ascii") if isinstance(qris_image, bytes) else qris_image
        transaction_state = transaction.state if transaction else False
        return {
            "success": bool(api_response.ok),
            "status_code": api_response.status_code,
            "error": False if api_response.ok else (api_response.text or _("Request API gagal.")),
            "transaction_id": transaction.id if transaction else False,
            "transaction_name": transaction.name if transaction else False,
            "payment_request_id": transaction_payload.get("payment_request_id"),
            "reference_id": transaction_payload.get("reference_id"),
            "state": transaction_state,
            "state_label": transaction_model._get_state_label(transaction_state),
            "xendit_status": transaction_payload.get("status"),
            "expires_at": transaction.expires_at and fields.Datetime.to_string(transaction.expires_at) if transaction else False,
            "qr_string": self._extract_qris_string_from_response(response_payload),
            "qris_image": qris_image_text,
            "response": response_payload,
        }

    def get_qris_transaction_status(self, transaction_id=None, payment_request_id=None):
        self.ensure_one()
        config = self.sudo()
        transaction_model = self.env["pos.payment.xendit.transaction"].sudo()
        domain = [("xendit_config_id", "=", config.id)]

        if transaction_id:
            try:
                transaction_id = int(transaction_id)
            except (TypeError, ValueError):
                raise ValidationError(_("Transaction ID tidak valid."))
            domain.append(("id", "=", transaction_id))
        elif payment_request_id:
            domain.append(("payment_request_id", "=", payment_request_id))
        else:
            raise ValidationError(_("Transaction ID atau Payment Request ID harus dikirim."))

        transaction = transaction_model.search(domain, limit=1)
        if not transaction:
            return {
                "found": False,
                "state": "draft",
                "state_label": transaction_model._get_state_label("draft"),
                "xendit_status": False,
            }

        return {
            "found": True,
            "transaction_id": transaction.id,
            "payment_request_id": transaction.payment_request_id,
            "state": transaction.state,
            "state_label": transaction_model._get_state_label(transaction.state),
            "xendit_status": transaction.xendit_status,
            "expires_at": transaction.expires_at and fields.Datetime.to_string(transaction.expires_at),
            "payment_date": transaction.payment_date and fields.Datetime.to_string(transaction.payment_date),
            "reference_id": transaction.reference_id,
        }

    def action_request_api(
        self,
        endpoint_url,
        request_body,
        response_field="response",
        generate_qris_image=False,
        body_label=None,
        create_transaction=False,
        transaction_context=None,
        return_payload=False,
    ):
        self.ensure_one()

        endpoint_url = (endpoint_url or "").strip()
        if not endpoint_url:
            raise ValidationError(_("Endpoint URL harus diisi."))

        body = self._load_request_body(request_body, body_label)

        headers = {
            "Accept": "application/json",
            # Xendit memakai Basic Auth dengan format "<secret_key>:" lalu di-encode base64.
            "Authorization": "Basic %s"
            % base64.b64encode(("%s:" % self.secret_key).encode("utf-8")).decode("utf-8"),
            "Content-Type": "application/json",
        }
        if self.api_version:
            headers["api-version"] = self.api_version

        try:
            # Response API disimpan ke field agar bisa dicek ulang dari tab Response.
            api_response = requests.post(endpoint_url, headers=headers, json=body, timeout=30)
        except requests.RequestException as error:
            _logger.exception("Xendit API request failed for config ID %s", self.id)
            raise UserError(_("Request ke Xendit gagal.\nDetail: %s") % error)

        response_payload = False
        try:
            response_payload = api_response.json()
            response_message = json.dumps(response_payload, indent=2)
        except ValueError:
            response_message = api_response.text or ""

        values = {
            response_field: response_message,
        }
        qris_image = False
        if generate_qris_image:
            qris_image = self._generate_qris_image_from_response(response_payload)
            values["qris_image"] = qris_image

        self.write(values)

        transaction = False
        if create_transaction and isinstance(response_payload, dict):
            transaction = self._create_xendit_transaction_from_response(
                response_payload,
                transaction_context=transaction_context,
            )

        if return_payload:
            return self._prepare_pos_qris_response(api_response, response_payload, qris_image, transaction)

        if not api_response.ok:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Xendit Respons"),
                    "message": _("Request API gagal. Cek tab Response."),
                    "sticky": True,
                    "type": "warning",
                },
            }

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Xendit Respons"),
                "message": _("Request API berhasil. Cek tab Response."),
                "sticky": False,
                "type": "success",
            },
        }
