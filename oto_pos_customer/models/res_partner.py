from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def oto_pos_customer_form_action(self, partner_id=False, defaults=None):
        view = self.env.ref("oto_pos_customer.view_oto_pos_quotation_form")
        return {
            "type": "ir.actions.act_window",
            "name": "Customer Vehicle Form",
            "res_model": "oto.pos.quotation.form",
            "views": [(view.id, "form")],
            "target": "new",
            "context": {
                "default_partner_id": partner_id or False,
                "default_partner_readonly": bool(partner_id),
                "dialog_size": "extra-large",
            },
        }
