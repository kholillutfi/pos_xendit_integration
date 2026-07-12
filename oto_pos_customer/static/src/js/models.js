odoo.define("oto_pos_customer.models", function (require) {
"use strict";

const models = require("point_of_sale.models");

models.load_models([
    {
        model: "vehicle.manufacture",
        fields: ["name", "code", "sequence"],
        loaded: function (self, vehicleManufactures) {
            self.vehicle_manufactures = vehicleManufactures;
        },
    },
    {
        model: "vehicle.model",
        fields: ["name", "vehicle_manufacture_id", "code", "sequence"],
        loaded: function (self, vehicleModels) {
            self.vehicle_models = vehicleModels;
        },
    },
    {
        model: "vehicle.type",
        fields: ["name", "vehicle_model_id", "vehicle_manufacture_id", "transmission_id", "code", "sequence"],
        loaded: function (self, vehicleTypes) {
            self.vehicle_types = vehicleTypes;
        },
    },
    {
        model: "vehicle.color",
        fields: ["name", "code", "sequence"],
        loaded: function (self, vehicleColors) {
            self.vehicle_colors = vehicleColors;
        },
    },
]);

});
