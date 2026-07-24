odoo.define("oto_pos_customer.ProductScreen", function (require) {
"use strict";

const ProductScreen = require("point_of_sale.ProductScreen");
const Registries = require("point_of_sale.Registries");

const OtoPosCustomerProductScreen = (ProductScreen) =>
    class extends ProductScreen {
        async _onClickPay() {
            const order = this.env.pos.get_order();
            if (order && order.get_orderlines().length && !order.get_client()) {
                await this.showPopup("ErrorPopup", {
                    title: this.env._t("Customer Required"),
                    body: this.env._t("Please select a customer before continuing to payment."),
                });
                return;
            }
            return super._onClickPay(...arguments);
        }
    };

Registries.Component.extend(ProductScreen, OtoPosCustomerProductScreen);

return ProductScreen;
});
