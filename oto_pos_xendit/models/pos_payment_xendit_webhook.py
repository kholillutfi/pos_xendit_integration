# -*- coding: utf-8 -*-

from odoo import fields, models


class PosPaymentXenditWebhook(models.Model):
    _name = "pos.payment.xendit.webhook"
    _description = "POS Payment Xendit Webhook"
    _order = "received_at desc, id desc"
    _rec_name = "transaction_id"

    transaction_id = fields.Char(string="Transaction ID")
    received_at = fields.Datetime(required=True, readonly=True)
    body = fields.Text(string="Response", readonly=True)
