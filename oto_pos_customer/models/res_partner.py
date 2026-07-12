from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_pos_pengguna_contact(self):
        self.ensure_one()
        return self.env["res.partner"].search(
            [
                ("parent_id", "=", self.id),
                "|",
                ("type", "=", "contact"),
                ("type", "=", False),
            ],
            order="id desc",
            limit=1,
        )

    @api.model
    def _prepare_pos_vehicle_history_vals(self, payload, partner):
        vehicle_history_vals = {"partner_id": partner.id}
        plate_number = (payload.get("vehicle_plate_number") or "").strip()
        vehicle_type_id = int(payload.get("vehicle_type_id")) if payload.get("vehicle_type_id") else False
        vehicle_model_id = int(payload.get("vehicle_model_id")) if payload.get("vehicle_model_id") else False
        vehicle_manufacture_id = int(payload.get("vehicle_manufacture_id")) if payload.get("vehicle_manufacture_id") else False
        vehicle_color_id = int(payload.get("vehicle_color_id")) if payload.get("vehicle_color_id") else False

        if plate_number:
            vehicle_history_vals.update(
                {
                    "name": plate_number,
                    "vehicle_plate_number": plate_number,
                }
            )

        if vehicle_type_id:
            vehicle_type = self.env["vehicle.type"].browse(vehicle_type_id).exists()
            if vehicle_type:
                vehicle_history_vals["vehicle_type_id"] = vehicle_type.id
                vehicle_history_vals["vehicle_model_id"] = (
                    vehicle_model_id or vehicle_type.vehicle_model_id.id or False
                )
                vehicle_history_vals["vehicle_manufacture_id"] = (
                    vehicle_manufacture_id or vehicle_type.vehicle_manufacture_id.id or False
                )
        elif vehicle_model_id:
            vehicle_model = self.env["vehicle.model"].browse(vehicle_model_id).exists()
            if vehicle_model:
                vehicle_history_vals["vehicle_model_id"] = vehicle_model.id
                vehicle_history_vals["vehicle_manufacture_id"] = (
                    vehicle_manufacture_id or vehicle_model.vehicle_manufacture_id.id or False
                )
        elif vehicle_manufacture_id:
            vehicle_history_vals["vehicle_manufacture_id"] = vehicle_manufacture_id

        if vehicle_color_id:
            vehicle_history_vals["vehicle_color_id"] = vehicle_color_id

        for field_name in ("vehicle_year", "vehicle_chassis_number", "vehicle_machine_number"):
            if field_name in payload:
                vehicle_history_vals[field_name] = (payload.get(field_name) or "").strip() or False

        if "vehicle_odometer" in payload:
            odometer = payload.get("vehicle_odometer")
            if odometer in ("", None, False):
                vehicle_history_vals["vehicle_odometer"] = 0.0
            else:
                try:
                    vehicle_history_vals["vehicle_odometer"] = float(odometer)
                except (TypeError, ValueError):
                    vehicle_history_vals["vehicle_odometer"] = 0.0

        return vehicle_history_vals

    def _upsert_pos_vehicle_history(self, payload):
        self.ensure_one()
        vehicle_payload_keys = {
            "vehicle_history_id",
            "vehicle_plate_number",
            "vehicle_year",
            "vehicle_type_id",
            "vehicle_manufacture_id",
            "vehicle_model_id",
            "vehicle_color_id",
            "vehicle_odometer",
            "vehicle_chassis_number",
            "vehicle_machine_number",
        }
        if not any(key in payload for key in vehicle_payload_keys):
            return

        history_vals = self._prepare_pos_vehicle_history_vals(payload, self)
        has_vehicle_value = any(
            history_vals.get(key)
            for key in history_vals
            if key != "partner_id"
        )
        if not has_vehicle_value:
            return

        vehicle_history = self.env["vehicle.customer.history"]
        vehicle_history_id = int(payload.get("vehicle_history_id")) if payload.get("vehicle_history_id") else False
        plate_number = history_vals.get("vehicle_plate_number")

        if vehicle_history_id:
            vehicle_history = self.env["vehicle.customer.history"].sudo().browse(vehicle_history_id).exists()
            if vehicle_history and vehicle_history.partner_id != self:
                vehicle_history = self.env["vehicle.customer.history"]

        if not vehicle_history and plate_number:
            vehicle_history = self.env["vehicle.customer.history"].sudo().search(
                [
                    ("partner_id", "=", self.id),
                    "|",
                    ("vehicle_plate_number", "=", plate_number),
                    ("name", "=", plate_number),
                ],
                limit=1,
            )

        if not vehicle_history and not plate_number:
            vehicle_history = self.env["vehicle.customer.history"].sudo().search(
                [("partner_id", "=", self.id)],
                order="id desc",
                limit=1,
            )

        if vehicle_history:
            vehicle_history.write(history_vals)
        elif history_vals.get("vehicle_plate_number") or history_vals.get("name"):
            self.env["vehicle.customer.history"].sudo().create(history_vals)

    def _upsert_pos_pengguna(self, payload):
        self.ensure_one()
        if "pengguna_name" not in payload and "pengguna_id" not in payload:
            return

        pengguna_name = (payload.get("pengguna_name") or "").strip()
        if not pengguna_name:
            return

        pengguna = self.env["res.partner"]
        pengguna_id = int(payload.get("pengguna_id")) if payload.get("pengguna_id") else False
        if pengguna_id:
            pengguna = self.env["res.partner"].sudo().browse(pengguna_id).exists()
            if pengguna and pengguna.parent_id != self:
                pengguna = self.env["res.partner"]

        if not pengguna:
            pengguna = self.sudo()._get_pos_pengguna_contact()

        pengguna_vals = {
            "name": pengguna_name,
            "parent_id": self.id,
            "type": "contact",
        }
        if pengguna:
            pengguna.write({"name": pengguna_name})
        else:
            self.env["res.partner"].sudo().create(pengguna_vals)

    @api.model
    def get_pos_customer_extra_data(self, partner_id):
        partner = self.sudo().browse(partner_id).exists()
        if not partner:
            return {}

        vehicle_history = self.env["vehicle.customer.history"].sudo().search(
            [("partner_id", "=", partner.id)],
            order="id desc",
            limit=1,
        )
        pengguna = partner._get_pos_pengguna_contact()

        return {
            "vehicle_history_id": vehicle_history.id or False,
            "vehicle_plate_number": vehicle_history.vehicle_plate_number or vehicle_history.name or "",
            "vehicle_year": vehicle_history.vehicle_year or "",
            "vehicle_type_id": vehicle_history.vehicle_type_id.id or False,
            "vehicle_manufacture_id": vehicle_history.vehicle_manufacture_id.id or False,
            "vehicle_model_id": vehicle_history.vehicle_model_id.id or False,
            "vehicle_color_id": vehicle_history.vehicle_color_id.id or False,
            "vehicle_odometer": vehicle_history.vehicle_odometer or "",
            "vehicle_chassis_number": vehicle_history.vehicle_chassis_number or "",
            "vehicle_machine_number": vehicle_history.vehicle_machine_number or "",
            "pengguna_id": pengguna.id or False,
            "pengguna_name": pengguna.name or "",
        }

    @api.model
    def create_from_ui(self, partner):
        custom_fields = {
            "vehicle_history_id",
            "vehicle_plate_number",
            "vehicle_year",
            "vehicle_type_id",
            "vehicle_manufacture_id",
            "vehicle_model_id",
            "vehicle_color_id",
            "vehicle_odometer",
            "vehicle_chassis_number",
            "vehicle_machine_number",
            "pengguna_id",
            "pengguna_name",
        }
        custom_payload = {key: partner.pop(key) for key in list(partner.keys()) if key in custom_fields}
        partner_id = super().create_from_ui(partner)
        partner_record = self.sudo().browse(partner_id).exists()
        if partner_record:
            partner_record._upsert_pos_vehicle_history(custom_payload)
            partner_record._upsert_pos_pengguna(custom_payload)
        return partner_id
