# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    xendit_payment_terminal = fields.Boolean(
        string="Xendit Payment Terminal",
        config_parameter="oto_pos_xendit.xendit_payment_terminal",
        help="Enable Xendit in the payment terminal selection on PoS payment methods.",
    )

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        pos_manager_group = self.env.ref("point_of_sale.group_pos_manager")
        xendit_group = self.env.ref("oto_pos_xendit.group_pos_xendit_manager")

        if self.xendit_payment_terminal:
            pos_manager_group.write({"implied_ids": [(4, xendit_group.id)]})
            return

        pos_manager_group.write({"implied_ids": [(3, xendit_group.id)]})
        xendit_group.write({"users": [(3, user.id) for user in pos_manager_group.users]})
        self.env["pos.payment.method"].search([("use_payment_terminal", "=", "xendit")]).write({
            "use_payment_terminal": False,
            "payment_xendit_config_id": False,
        })
