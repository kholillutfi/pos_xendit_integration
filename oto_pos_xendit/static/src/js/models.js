odoo.define("oto_pos_xendit.models", function (require) {
"use strict";

const models = require("point_of_sale.models");
const PaymentXendit = require("oto_pos_xendit.payment");

models.load_fields("pos.payment.method", "payment_xendit_config_pos_id");
models.register_payment_method("xendit", PaymentXendit);
});
