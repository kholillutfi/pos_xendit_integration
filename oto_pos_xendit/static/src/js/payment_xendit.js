odoo.define("oto_pos_xendit.payment", function (require) {
"use strict";

const core = require("web.core");
const ajax = require("web.ajax");
const AbstractAwaitablePopup = require("point_of_sale.AbstractAwaitablePopup");
const { Gui } = require("point_of_sale.Gui");
const PaymentInterface = require("point_of_sale.PaymentInterface");
const Registries = require("point_of_sale.Registries");
const XenditPaymentScreen = require("oto_pos_xendit.payment_screen");

const _t = core._t;
let activeXenditPopup = null;

class XenditQrisPopup extends AbstractAwaitablePopup {
    mounted() {
        if (super.mounted) {
            super.mounted();
        }
        activeXenditPopup = this;
    }

    willUnmount() {
        if (activeXenditPopup === this) {
            activeXenditPopup = null;
        }
        if (super.willUnmount) {
            super.willUnmount();
        }
    }
}
XenditQrisPopup.template = "XenditQrisPopup";
XenditQrisPopup.defaultProps = {
    title: _t("Xendit QRIS"),
};
Registries.Component.add(XenditQrisPopup);

const PaymentXendit = PaymentInterface.extend({
    send_payment_request: function (cid) {
        const self = this;
        this._super.apply(this, arguments);

        const order = this.pos.get_order();
        const paymentline = order && order.get_paymentline(cid);
        const configId = this._get_xendit_config_id();

        if (!paymentline) {
            this._show_error(_t("Payment line tidak ditemukan."));
            return Promise.resolve(false);
        }
        if (!configId) {
            this._show_error(_t("Payment method QRIS belum punya Xendit Configuration."));
            return Promise.resolve(false);
        }

        const lockedAmount = this._get_locked_amount(order, paymentline);
        if (!lockedAmount || lockedAmount <= 0) {
            this._show_error(_t("Nominal QRIS harus mengikuti sisa tagihan dan lebih besar dari 0."));
            return Promise.resolve(false);
        }

        const requestPayload = Object.assign({
            amount: lockedAmount,
            pos_order_uid: order.uid,
            pos_reference: order.name || order.uid,
            payment_method_id: paymentline.payment_method.id,
            payment_line_cid: cid,
            order_lines: this._collect_order_lines(order),
        }, this._collect_cashier_data());

        return ajax.jsonRpc("/pos/xendit/request_qris", "call", {
            config_id: configId,
            pos_payload: requestPayload,
        }).then(function (response) {
            if (!response || !response.success) {
                self._show_error(response && response.error ? response.error : _t("Request QRIS gagal."));
                return false;
            }

            paymentline.xendit_transaction_id = response.transaction_id;
            paymentline.xendit_payment_request_id = response.payment_request_id;
            if (response.payment_request_id) {
                paymentline.transaction_id = response.payment_request_id;
            }
            if (paymentline.set_receipt_info) {
                paymentline.set_receipt_info(
                    "Xendit QRIS<br/>Payment Request: " + (response.payment_request_id || "-")
                    + "<br/>Reference: " + (response.reference_id || "-")
                );
            }

            const popupPromise = Gui.showPopup("XenditQrisPopup", {
                qrisImage: response.qris_image ? "data:image/png;base64," + response.qris_image : false,
                qrString: response.qr_string,
                paymentRequestId: response.payment_request_id,
                referenceId: response.reference_id,
                amount: self.pos.format_currency(lockedAmount),
                status: response.state_label || response.state || "-",
                expiresAt: response.expires_at,
            });

            return self._wait_for_transaction_update(configId, order, paymentline, response, popupPromise);
        }).catch(function (error) {
            self._show_error(self._get_error_message(error));
            return false;
        });
    },

    send_payment_cancel: function () {
        this._super.apply(this, arguments);
        return Promise.resolve(true);
    },

    _get_xendit_config_id: function () {
        if (this.payment_method.payment_xendit_config_pos_id) {
            return this.payment_method.payment_xendit_config_pos_id;
        }
        const config = this.payment_method.payment_xendit_config_id;
        if (Array.isArray(config)) {
            return config[0];
        }
        return config || false;
    },

    _show_error: function (body) {
        Gui.showPopup("ErrorPopup", {
            title: _t("Xendit QRIS"),
            body: body,
        });
    },

    _collect_order_lines: function (order) {
        return (order && order.get_orderlines ? order.get_orderlines() : []).map(function (line) {
            const product = line.get_product ? line.get_product() : false;
            const productName = line.get_full_product_name
                ? line.get_full_product_name()
                : product && product.display_name
                    ? product.display_name
                    : "-";

            return {
                product_id: product && product.id ? product.id : false,
                product_name: productName,
                qty: line.get_quantity ? line.get_quantity() : 0,
            };
        });
    },

    _collect_cashier_data: function () {
        const cashier = this.pos.get_cashier ? this.pos.get_cashier() : false;
        const sessionUser = this.pos.pos_session && this.pos.pos_session.user_id ? this.pos.pos_session.user_id : false;
        const cashierType = this.pos.config && this.pos.config.module_pos_hr ? "employee" : "user";

        return {
            cashier_id: cashier && cashier.id ? cashier.id : false,
            cashier_name: cashier && (cashier.name || cashier.display_name) ? (cashier.name || cashier.display_name) : (sessionUser && sessionUser[1]) || false,
            cashier_type: cashierType,
            session_user_id: sessionUser && sessionUser[0] ? sessionUser[0] : false,
            session_user_name: sessionUser && sessionUser[1] ? sessionUser[1] : false,
        };
    },

    _get_locked_amount: function (order, paymentline) {
        if (!order || !paymentline) {
            return 0;
        }

        const lockedAmount = order.get_due ? order.get_due(paymentline) : paymentline.amount || 0;
        if (paymentline.set_amount) {
            paymentline.set_amount(lockedAmount);
        }
        return paymentline.get_amount ? paymentline.get_amount() : paymentline.amount;
    },

    _wait_for_transaction_update: function (configId, order, paymentline, response, popupPromise) {
        const self = this;
        const transactionId = response.transaction_id;
        let stopped = false;
        let pollTimeout = false;
        let popupClosed = false;

        const stop = function () {
            stopped = true;
            if (pollTimeout) {
                clearTimeout(pollTimeout);
                pollTimeout = false;
            }
        };

        const closePopup = function (confirmed) {
            if (popupClosed) {
                return;
            }
            popupClosed = true;
            self._close_active_popup(confirmed);
        };

        return new Promise(function (resolve) {
            const pollStatus = function () {
                if (stopped) {
                    return;
                }

                ajax.jsonRpc("/pos/xendit/transaction_status", "call", {
                    config_id: configId,
                    transaction_id: transactionId,
                    payment_request_id: response.payment_request_id,
                }).then(function (statusResult) {
                    if (stopped) {
                        return;
                    }

                    if (statusResult && statusResult.state === "paid") {
                        stop();
                        closePopup(true);
                        resolve(true);
                        self._schedule_auto_validate_order(order);
                        return;
                    }

                    if (statusResult && ["failed", "expired", "cancelled"].includes(statusResult.state)) {
                        stop();
                        self._set_paymentline_status(paymentline, "retry");
                        closePopup(false);
                        self._show_error(_t("Transaksi QRIS berstatus: ") + statusResult.state);
                        resolve(false);
                        return;
                    }

                    pollTimeout = setTimeout(pollStatus, 3000);
                }).catch(function () {
                    if (stopped) {
                        return;
                    }
                    pollTimeout = setTimeout(pollStatus, 3000);
                });
            };

            pollTimeout = setTimeout(pollStatus, 3000);

            popupPromise.then(function (popupResult) {
                if (stopped) {
                    return;
                }
                stop();
                if (!popupResult || !popupResult.confirmed) {
                    self._cancel_xendit_transaction(configId, response).then(function (cancelResult) {
                        if (cancelResult && cancelResult.state === "paid") {
                            resolve(true);
                            self._schedule_auto_validate_order(order);
                            return;
                        }
                        self._set_paymentline_status(paymentline, "retry");
                        resolve(false);
                    });
                    return;
                }
                resolve(false);
            });

            popupPromise.catch(function () {
                if (stopped) {
                    return;
                }
                stop();
                resolve(false);
            });
        });
    },

    _cancel_xendit_transaction: function (configId, response) {
        const self = this;
        return ajax.jsonRpc("/pos/xendit/cancel_transaction", "call", {
            config_id: configId,
            transaction_id: response.transaction_id,
            payment_request_id: response.payment_request_id,
        }).catch(function (error) {
            self._show_error(self._get_error_message(error));
            return false;
        });
    },

    _set_paymentline_status: function (paymentline, status) {
        if (paymentline && paymentline.set_payment_status) {
            paymentline.set_payment_status(status);
        }
    },

    _close_active_popup: function (confirmed) {
        if (!activeXenditPopup) {
            return;
        }
        if (confirmed) {
            activeXenditPopup.confirm();
            return;
        }
        activeXenditPopup.cancel();
    },

    _schedule_auto_validate_order: function (order) {
        const self = this;
        setTimeout(function () {
            self._auto_validate_order(order);
        }, 250);
    },

    _auto_validate_order: function (order) {
        const paymentScreen = XenditPaymentScreen.getActivePaymentScreen
            ? XenditPaymentScreen.getActivePaymentScreen()
            : false;

        if (!paymentScreen || !order) {
            return Promise.resolve(true);
        }

        return paymentScreen.autoValidateXenditOrder(order.uid);
    },

    _get_error_message: function (error) {
        if (error && error.data && error.data.message) {
            return error.data.message;
        }
        if (error && error.message && error.message.data && error.message.data.message) {
            return error.message.data.message;
        }
        if (error && typeof error.message === "string") {
            return error.message;
        }
        return _t("Request QRIS ke backend gagal.");
    },
});

return PaymentXendit;
});
