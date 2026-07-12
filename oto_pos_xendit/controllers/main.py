# -*- coding: utf-8 -*-

import json
import logging

from odoo import _, fields, http
from odoo.exceptions import ValidationError
from odoo.http import request, Response


_logger = logging.getLogger(__name__)


class OtoPosXenditController(http.Controller):
    @http.route('/pos/xendit/request_qris', type='json', auth='user', methods=['POST'], csrf=False)
    def pos_xendit_request_qris(self, config_id, pos_payload=None):
        try:
            config_id = int(config_id)
        except (TypeError, ValueError):
            raise ValidationError(_("Konfigurasi Xendit tidak valid."))

        xendit_config = request.env["pos.payment.xendit.config"].sudo().browse(config_id).exists()
        if not xendit_config:
            raise ValidationError(_("Konfigurasi Xendit tidak ditemukan."))

        return xendit_config.action_request_qris(pos_payload or {})

    @http.route('/pos/xendit/transaction_status', type='json', auth='user', methods=['POST'], csrf=False)
    def pos_xendit_transaction_status(self, config_id, transaction_id=None, payment_request_id=None):
        try:
            config_id = int(config_id)
        except (TypeError, ValueError):
            raise ValidationError(_("Konfigurasi Xendit tidak valid."))

        xendit_config = request.env["pos.payment.xendit.config"].sudo().browse(config_id).exists()
        if not xendit_config:
            raise ValidationError(_("Konfigurasi Xendit tidak ditemukan."))

        return xendit_config.get_qris_transaction_status(transaction_id, payment_request_id)

    @http.route('/pos/xendit/cancel_transaction', type='json', auth='user', methods=['POST'], csrf=False)
    def pos_xendit_cancel_transaction(self, config_id, transaction_id=None, payment_request_id=None):
        try:
            config_id = int(config_id)
        except (TypeError, ValueError):
            raise ValidationError(_("Konfigurasi Xendit tidak valid."))

        xendit_config = request.env["pos.payment.xendit.config"].sudo().browse(config_id).exists()
        if not xendit_config:
            raise ValidationError(_("Konfigurasi Xendit tidak ditemukan."))

        return request.env["pos.payment.xendit.transaction"].sudo().cancel_from_pos(
            xendit_config,
            transaction_id=transaction_id,
            payment_request_id=payment_request_id,
        )

    @http.route('/pos/xendit/webhook', type='json', auth='public', methods=['GET', 'POST'], csrf=False)
    def xendit_qris_webhook(self, **kwargs):
        _logger.info("=== XENDIT WEBHOOK HIT ===")
        _logger.info("Method: %s", request.httprequest.method)
        _logger.info("Headers: %s", dict(request.httprequest.headers))

        callback_token = (
            request.httprequest.headers.get("X-Callback-Token")
            or request.httprequest.headers.get("Callback-Token")
        )
        if not callback_token:
            _logger.warning("Xendit webhook rejected: missing callback token")
            return Response("Missing callback token", status=400)

        xendit_config = request.env["pos.payment.xendit.config"].sudo().search(
            [("webhook_token", "=", callback_token)],
            limit=1,
        )
        if not xendit_config:
            _logger.warning("Xendit webhook rejected: invalid callback token")
            return Response("Invalid callback token", status=401)

        raw_body = request.httprequest.data or b''
        # _logger.info("Raw body: %s", raw_body)
        raw_body_text = raw_body.decode("utf-8", errors="replace") if raw_body else ""

        webhook_vals = {
            "transaction_id": False,
            "received_at": fields.Datetime.now(),
            "body": raw_body_text,
        }
        payload = {}
        if raw_body:
            try:
                payload = json.loads(raw_body.decode('utf-8'))
                _logger.info("Payload JSON: %s", json.dumps(payload, indent=2))
                pretty_payload = json.dumps(payload, indent=2)
                transaction_payload = payload.get("data") if isinstance(payload.get("data"), dict) else payload
                webhook_vals.update({
                    "transaction_id": transaction_payload.get("payment_request_id") or transaction_payload.get("id"),
                    "body": pretty_payload,
                })
                xendit_config.write({"payment_response": pretty_payload})
            except Exception:
                xendit_config.write({"payment_response": raw_body_text})
                request.env["pos.payment.xendit.webhook"].sudo().create(webhook_vals)
                _logger.exception("Failed parse webhook payload")
                return Response("Invalid JSON", status=400)
        else:
            xendit_config.write({"payment_response": raw_body_text})

        webhook = request.env["pos.payment.xendit.webhook"].sudo().create(webhook_vals)
        if payload:
            request.env["pos.payment.xendit.transaction"].sudo().update_status_from_webhook(
                xendit_config,
                payload,
                webhook=webhook,
            )

        return Response("Xendit webhook OK", status=200)    
