odoo.define("oto_pos_customer.ClientDetailsEdit", function (require) {
"use strict";

const ClientDetailsEdit = require("point_of_sale.ClientDetailsEdit");
const Registries = require("point_of_sale.Registries");

const OtoPosCustomerClientDetailsEdit = (ClientDetailsEdit) =>
    class extends ClientDetailsEdit {
        constructor() {
            super(...arguments);
            this.intFields.push(
                "vehicle_history_id",
                "pengguna_id",
                "vehicle_manufacture_id",
                "vehicle_model_id",
                "vehicle_type_id",
                "vehicle_color_id"
            );
            this.extraData = this._getEmptyExtraData();
        }

        mounted() {
            super.mounted();
            this._loadPartnerExtraData();
        }

        _getEmptyExtraData() {
            return {
                vehicle_history_id: false,
                vehicle_plate_number: "",
                vehicle_year: "",
                vehicle_manufacture_id: false,
                vehicle_model_id: false,
                vehicle_type_id: false,
                vehicle_color_id: false,
                vehicle_odometer: "",
                vehicle_chassis_number: "",
                vehicle_machine_number: "",
                pengguna_id: false,
                pengguna_name: "",
            };
        }

        async _loadPartnerExtraData() {
            const partner = this.props.partner || {};
            if (!partner.id) {
                this.extraData = this._getEmptyExtraData();
                this.changes.vehicle_history_id = false;
                this.changes.pengguna_id = false;
                return;
            }
            const extraData = await this.rpc({
                model: "res.partner",
                method: "get_pos_customer_extra_data",
                args: [partner.id],
            });
            this.extraData = Object.assign(this._getEmptyExtraData(), extraData || {});
            this.changes.vehicle_history_id = this.extraData.vehicle_history_id || false;
            this.changes.pengguna_id = this.extraData.pengguna_id || false;
            this.render();
        }

        _getFieldValue(fieldName) {
            if (Object.prototype.hasOwnProperty.call(this.changes, fieldName)) {
                return this.changes[fieldName] || "";
            }
            return this.extraData[fieldName] || "";
        }

        get selectedVehicleManufactureId() {
            return parseInt(this._getFieldValue("vehicle_manufacture_id")) || false;
        }

        get selectedVehicleModelId() {
            return parseInt(this._getFieldValue("vehicle_model_id")) || false;
        }

        get selectedVehicleTypeId() {
            return parseInt(this._getFieldValue("vehicle_type_id")) || false;
        }

        get selectedVehicleColorId() {
            return parseInt(this._getFieldValue("vehicle_color_id")) || false;
        }

        get selectedVehicleType() {
            return (this.env.pos.vehicle_types || []).find(
                (vehicleType) => vehicleType.id === this.selectedVehicleTypeId
            );
        }

        get vehicleManufactures() {
            return this.env.pos.vehicle_manufactures || [];
        }

        get vehicleModels() {
            const vehicleModels = this.env.pos.vehicle_models || [];
            if (!this.selectedVehicleManufactureId) {
                return vehicleModels;
            }
            return vehicleModels.filter(
                (vehicleModel) =>
                    vehicleModel.vehicle_manufacture_id &&
                    vehicleModel.vehicle_manufacture_id[0] === this.selectedVehicleManufactureId
            );
        }

        get vehicleTypes() {
            return (this.env.pos.vehicle_types || []).filter((vehicleType) => {
                const sameManufacture =
                    !this.selectedVehicleManufactureId ||
                    (
                        vehicleType.vehicle_manufacture_id &&
                        vehicleType.vehicle_manufacture_id[0] === this.selectedVehicleManufactureId
                    );
                const sameModel =
                    !this.selectedVehicleModelId ||
                    (
                        vehicleType.vehicle_model_id &&
                        vehicleType.vehicle_model_id[0] === this.selectedVehicleModelId
                    );
                return sameManufacture && sameModel;
            });
        }

        get vehicleColors() {
            return this.env.pos.vehicle_colors || [];
        }

        get transmissionName() {
            return this.selectedVehicleType && this.selectedVehicleType.transmission_id
                ? this.selectedVehicleType.transmission_id[1]
                : "";
        }

        captureChange(event) {
            super.captureChange(event);
            const fieldName = event.target.name;
            const currentValue = parseInt(event.target.value) || false;

            if (fieldName === "vehicle_type_id") {
                const vehicleType = this.selectedVehicleType;
                if (vehicleType) {
                    this.changes.vehicle_model_id = vehicleType.vehicle_model_id
                        ? vehicleType.vehicle_model_id[0]
                        : "";
                    this.changes.vehicle_manufacture_id = vehicleType.vehicle_manufacture_id
                        ? vehicleType.vehicle_manufacture_id[0]
                        : "";
                }
                this.render();
                return;
            }

            if (fieldName === "vehicle_model_id") {
                const vehicleModel = (this.env.pos.vehicle_models || []).find(
                    (model) => model.id === currentValue
                );
                if (vehicleModel && vehicleModel.vehicle_manufacture_id) {
                    this.changes.vehicle_manufacture_id = vehicleModel.vehicle_manufacture_id[0];
                }
                if (
                    this.selectedVehicleType &&
                    this.selectedVehicleType.vehicle_model_id &&
                    this.selectedVehicleType.vehicle_model_id[0] !== currentValue
                ) {
                    this.changes.vehicle_type_id = "";
                }
                this.render();
                return;
            }

            if (fieldName === "vehicle_manufacture_id") {
                const selectedModel = (this.env.pos.vehicle_models || []).find(
                    (model) => model.id === this.selectedVehicleModelId
                );
                if (
                    selectedModel &&
                    (
                        !selectedModel.vehicle_manufacture_id ||
                        selectedModel.vehicle_manufacture_id[0] !== currentValue
                    )
                ) {
                    this.changes.vehicle_model_id = "";
                }
                if (
                    this.selectedVehicleType &&
                    this.selectedVehicleType.vehicle_manufacture_id &&
                    this.selectedVehicleType.vehicle_manufacture_id[0] !== currentValue
                ) {
                    this.changes.vehicle_type_id = "";
                }
                this.render();
            }
        }
    };

Registries.Component.extend(ClientDetailsEdit, OtoPosCustomerClientDetailsEdit);

return ClientDetailsEdit;
});
