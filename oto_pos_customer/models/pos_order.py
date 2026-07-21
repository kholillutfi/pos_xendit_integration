from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    oto_pos_quotation_form_id = fields.Many2one(
        "oto.pos.quotation.form",
        string="Service Information",
        copy=False,
        index=True,
        ondelete="set null",
    )

    @api.model
    def _order_fields(self, ui_order):
        values = super()._order_fields(ui_order)
        form_id = ui_order.get("oto_pos_quotation_form_id")
        form = self.env["oto.pos.quotation.form"].browse(form_id).exists() if form_id else False

        # Never connect an order to a form owned by another customer.
        if form and form.partner_id.id == ui_order.get("partner_id"):
            values["oto_pos_quotation_form_id"] = form.id
        else:
            values["oto_pos_quotation_form_id"] = False
        return values
