from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    customer_unique_no = fields.Char(
        string="Unique Customer No",
        copy=False,
        readonly=True,
        index=True,
    )

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

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("customer_unique_no") or vals.get("parent_id"):
                continue
            vals["customer_unique_no"] = sequence.next_by_code("oto_pos_customer.unique_no") or "/"
        return super().create(vals_list)
