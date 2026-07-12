odoo.define("oto_pos_xendit.payment_screen", function (require) {
"use strict";

const PaymentScreen = require("point_of_sale.PaymentScreen");
const NumberBuffer = require("point_of_sale.NumberBuffer");
const Registries = require("point_of_sale.Registries");

let activePaymentScreen = null;

const XenditPaymentScreen = (PaymentScreen) =>
    class extends PaymentScreen {
        mounted() {
            if (super.mounted) {
                super.mounted();
            }
            activePaymentScreen = this;
        }

        willUnmount() {
            if (activePaymentScreen === this) {
                activePaymentScreen = null;
            }
            if (super.willUnmount) {
                super.willUnmount();
            }
        }

        _updateSelectedPaymentline() {
            const paymentLine = this.selectedPaymentLine;
            const isXenditLine = paymentLine
                && paymentLine.payment_method
                && paymentLine.payment_method.use_payment_terminal === "xendit";

            if (isXenditLine) {
                NumberBuffer.reset();
                this.render();
                return;
            }

            super._updateSelectedPaymentline(...arguments);
        }

        async autoValidateXenditOrder(orderUid) {
            const currentOrder = this.currentOrder || (this.env.pos && this.env.pos.get_order ? this.env.pos.get_order() : false);
            if (!currentOrder || currentOrder.uid !== orderUid || this._xenditAutoValidating) {
                return false;
            }

            this._xenditAutoValidating = true;
            try {
                await this.validateOrder(false);
                return true;
            } finally {
                this._xenditAutoValidating = false;
            }
        }
    };

Registries.Component.extend(PaymentScreen, XenditPaymentScreen);

return {
    getActivePaymentScreen() {
        return activePaymentScreen;
    },
};
});
