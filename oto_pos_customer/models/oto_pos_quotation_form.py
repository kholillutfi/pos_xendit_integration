from odoo import api, fields, models


class OtoPosQuotationForm(models.Model):
    _name = "oto.pos.quotation.form"
    _description = "POS Customer Vehicle Form"
    _rec_name = "partner_id"
    _order = "id desc"

    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
        index=True,
        ondelete="restrict",
    )
    partner_readonly = fields.Boolean(default=False)
    vehicle_plate_number_id = fields.Many2one(
        "vehicle.customer.history",
        string="Plat Nomor",
        index=True,
        ondelete="restrict",
    )
    vehicle_year = fields.Char(string="Tahun")
    transmission_id = fields.Many2one(
        "vehicle.transmission",
        string="Transmisi",
        ondelete="restrict",
    )
    vehicle_chassis_number = fields.Char(string="Nomor Rangka")
    vehicle_machine_number = fields.Char(string="Nomor Mesin")
    vehicle_type_id = fields.Many2one(
        "vehicle.type",
        string="Vehicle Type",
        ondelete="restrict",
    )
    vehicle_color_id = fields.Many2one(
        "vehicle.color",
        string="Warna",
        ondelete="restrict",
    )
    vehicle_manufacture_id = fields.Many2one(
        "vehicle.manufacture",
        string="Vehicle Manufacture",
        ondelete="restrict",
    )
    vehicle_odometer = fields.Float(string="Odometer", digits=(12, 0))
    vehicle_model_id = fields.Many2one(
        "vehicle.model",
        string="Vehicle Model",
        ondelete="restrict",
    )
    complaint_note = fields.Text(string="Keluhan")
    saran = fields.Text(string="Saran")

    @api.model
    def _vehicle_default_values(self, vehicle):
        return {
            "vehicle_plate_number_id": vehicle.id,
            "vehicle_year": vehicle.vehicle_year,
            "transmission_id": vehicle.vehicle_type_id.transmission_id.id,
            "vehicle_chassis_number": vehicle.vehicle_chassis_number,
            "vehicle_machine_number": vehicle.vehicle_machine_number,
            "vehicle_type_id": vehicle.vehicle_type_id.id,
            "vehicle_color_id": vehicle.vehicle_color_id.id,
            "vehicle_manufacture_id": vehicle.vehicle_manufacture_id.id,
            "vehicle_odometer": vehicle.vehicle_odometer,
            "vehicle_model_id": vehicle.vehicle_model_id.id,
        }

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        partner_id = values.get("partner_id") or self.env.context.get("default_partner_id")
        if not partner_id:
            return values

        vehicle = self.env["vehicle.customer.history"].search(
            [("partner_id", "=", partner_id)],
            order="id desc",
            limit=1,
        )
        if vehicle:
            vehicle_values = self._vehicle_default_values(vehicle)
            values.update(
                {
                    field_name: field_value
                    for field_name, field_value in vehicle_values.items()
                    if field_name in fields_list
                }
            )
        return values

    @api.onchange("vehicle_plate_number_id")
    def _onchange_vehicle_plate_number_id(self):
        vehicle = self.vehicle_plate_number_id
        if not vehicle:
            return

        self.update(self._vehicle_default_values(vehicle))
        self.partner_id = vehicle.partner_id

    @api.onchange("vehicle_type_id")
    def _onchange_vehicle_type_id(self):
        if self.vehicle_type_id:
            self.vehicle_model_id = self.vehicle_type_id.vehicle_model_id
            self.vehicle_manufacture_id = self.vehicle_type_id.vehicle_manufacture_id
            self.transmission_id = self.vehicle_type_id.transmission_id

    @api.onchange("vehicle_model_id")
    def _onchange_vehicle_model_id(self):
        if self.vehicle_model_id:
            self.vehicle_manufacture_id = self.vehicle_model_id.vehicle_manufacture_id

    @api.model
    def oto_pos_partner_from_form(self, form_id):
        form = self.browse(form_id).exists()
        return form.partner_id.id if form else False
