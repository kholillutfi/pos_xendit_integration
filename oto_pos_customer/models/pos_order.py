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

    def _oto_pos_invoice_58_empty(self, value):
        if value or value == 0:
            return value
        return "-"

    def _oto_pos_invoice_58_display(self, record):
        return record.display_name if record else "-"

    def _oto_pos_invoice_58_date(self, value):
        if not value:
            return "-"
        return fields.Datetime.context_timestamp(self, value).strftime("%Y-%m-%d")

    def _oto_pos_invoice_58_branch(self):
        self.ensure_one()
        branch = False
        if "branch_id" in self.user_id._fields:
            branch = self.user_id.branch_id
        if not branch and "branch_id" in self.env.user._fields:
            branch = self.env.user.branch_id
        return branch

    def oto_pos_invoice_58_values(self):
        self.ensure_one()
        service = self.oto_pos_quotation_form_id
        partner = self.partner_id
        branch = self._oto_pos_invoice_58_branch()
        discount_total = sum(
            (line.price_unit * line.qty) * ((line.discount or 0.0) / 100.0)
            for line in self.lines
        )
        amount_untaxed = sum(self.lines.mapped("price_subtotal"))
        model_year = " ".join(
            value
            for value in [
                service.vehicle_type_id.name if service.vehicle_type_id else "",
                service.vehicle_year or "",
            ]
            if value
        )
        return {
            "branch_name": self._oto_pos_invoice_58_display(branch),
            "branch_address": self._oto_pos_invoice_58_empty(branch.address if branch else False),
            "receipt_no": self._oto_pos_invoice_58_empty(self.name),
            "receipt_date": self._oto_pos_invoice_58_date(self.date_order),
            "plate_no": self._oto_pos_invoice_58_display(service.vehicle_plate_number_id if service else False),
            "service_order": self._oto_pos_invoice_58_empty(self.pos_reference or self.name),
            "service_order_date": self._oto_pos_invoice_58_date(self.date_order),
            "model_year": self._oto_pos_invoice_58_empty(model_year),
            "odometer": int(service.vehicle_odometer) if service and service.vehicle_odometer else "-",
            "mechanic": self._oto_pos_invoice_58_empty(self.user_id.name),
            "customer_id": self._oto_pos_invoice_58_empty(partner.id if partner else False),
            "npwp": self._oto_pos_invoice_58_empty(partner.vat if partner else False),
            "nik": self._oto_pos_invoice_58_empty(partner.ktp_number if partner and "ktp_number" in partner._fields else False),
            "email": self._oto_pos_invoice_58_empty(partner.email if partner else False),
            "customer_name": self._oto_pos_invoice_58_empty(partner.name if partner else False),
            "phone": self._oto_pos_invoice_58_empty((partner.mobile or partner.phone) if partner else False),
            "address": self._oto_pos_invoice_58_empty(partner.street if partner else False),
            "amount_untaxed": amount_untaxed,
            "amount_tax": self.amount_tax,
            "amount_total": self.amount_total,
            "discount_total": -discount_total,
            "advance_amount": 0.0,
            "grand_total": self.amount_total,
            "saran": self._oto_pos_invoice_58_empty(service.saran if service else False),
        }

    def action_oto_pos_invoice_58(self):
        return self.env.ref("oto_pos_customer.action_report_pos_invoice_58").report_action(self)
