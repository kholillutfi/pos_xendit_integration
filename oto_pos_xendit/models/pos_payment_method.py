# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    payment_xendit_config_id = fields.Many2one(
        "pos.payment.xendit.config",
        string="Xendit QRIS Configuration",
        ondelete="restrict",
    )
    payment_xendit_config_pos_id = fields.Integer(
        string="Xendit QRIS Configuration ID",
        compute="_compute_payment_xendit_config_pos_id",
    )

    def _compute_payment_xendit_config_pos_id(self):
        for payment_method in self:
            payment_method.payment_xendit_config_pos_id = payment_method.payment_xendit_config_id.id

    def _get_payment_terminal_selection(self):
        selection_list = super(PosPaymentMethod, self)._get_payment_terminal_selection()
        if self.env["ir.config_parameter"].sudo().get_param("oto_pos_xendit.xendit_payment_terminal"):
            selection_list.append(("xendit", "Xendit"))
        return selection_list

    @api.onchange("use_payment_terminal")
    def _onchange_use_payment_terminal(self):
        super(PosPaymentMethod, self)._onchange_use_payment_terminal()
        if self.use_payment_terminal != "xendit":
            self.payment_xendit_config_id = False
