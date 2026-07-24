odoo.define("oto_pos_customer.ClientListScreen", function (require) {
"use strict";

const ClientListScreen = require("point_of_sale.ClientListScreen");
const FormController = require("web.FormController");
const Registries = require("point_of_sale.Registries");
const models = require("point_of_sale.models");
const { isConnectionError } = require("point_of_sale.utils");

const CUSTOMER_FORM_DIALOG_CLASS = "oto-pos-customer-form-dialog";
const CUSTOMER_FORM_OPEN_CLASS = "oto-pos-customer-form-open";

models.load_fields("res.partner", ["ktp_number"]);
models.load_fields("res.users", ["branch_id"]);

models.load_models({
    model: "res.branch",
    fields: ["name", "address"],
    domain: function (self) {
        const branchIds = (self.users || [])
            .map((user) => user.branch_id && user.branch_id[0])
            .filter((branchId) => branchId);
        return [["id", "in", branchIds]];
    },
    loaded: function (self, branches) {
        self.oto_pos_branches_by_id = {};
        branches.forEach((branch) => {
            self.oto_pos_branches_by_id[branch.id] = branch;
        });
    },
}, { after: "res.users" });

const PosOrderSuper = models.Order.prototype;
models.Order = models.Order.extend({
    init_from_JSON(json) {
        PosOrderSuper.init_from_JSON.apply(this, arguments);
        this.oto_pos_quotation_form_id = json.oto_pos_quotation_form_id || false;
        this.oto_pos_quotation_form_partner_id = this.oto_pos_quotation_form_id
            ? json.partner_id || false
            : false;
        this.oto_pos_receipt_info = json.oto_pos_receipt_info || {};
    },

    export_as_JSON() {
        const json = PosOrderSuper.export_as_JSON.apply(this, arguments);
        json.oto_pos_quotation_form_id = this.oto_pos_quotation_form_id || false;
        json.oto_pos_receipt_info = this.oto_pos_receipt_info || {};
        return json;
    },

    export_for_printing() {
        const receipt = PosOrderSuper.export_for_printing.apply(this, arguments);
        const client = this.get_client();
        const user = this.pos.user;
        const branchId = user && user.branch_id && user.branch_id[0];
        const branch = branchId && this.pos.oto_pos_branches_by_id
            ? this.pos.oto_pos_branches_by_id[branchId]
            : false;
        receipt.oto_pos_58 = {
            branch_name: branch ? branch.name : "-",
            branch_address: branch && branch.address ? branch.address : "-",
            receipt_no: receipt.name || "-",
            receipt_date: receipt.date.localestring || receipt.date.validation_date || "-",
            plate_no: this.oto_pos_receipt_info.plate_no || "-",
            service_order: receipt.name || "-",
            service_order_date: receipt.date.localestring || receipt.date.validation_date || "-",
            model_year: this.oto_pos_receipt_info.model_year || "-",
            odometer: this.oto_pos_receipt_info.odometer || "-",
            mechanic: user && user.name ? user.name : "-",
            customer_id: client ? client.id : "-",
            npwp: client && client.vat ? client.vat : "-",
            nik: client && client.ktp_number ? client.ktp_number : "-",
            email: client && client.email ? client.email : "-",
            customer_name: client && client.name ? client.name : "-",
            phone: client && (client.mobile || client.phone) ? client.mobile || client.phone : "-",
            address: client && client.street ? client.street : "-",
            saran: this.oto_pos_receipt_info.saran || "-",
        };
        return receipt;
    },

    set_client(client) {
        if (
            !client ||
            (
                this.oto_pos_quotation_form_partner_id &&
                this.oto_pos_quotation_form_partner_id !== client.id
            )
        ) {
            this.oto_pos_quotation_form_id = false;
            this.oto_pos_quotation_form_partner_id = false;
            this.oto_pos_receipt_info = {};
        }
        return PosOrderSuper.set_client.apply(this, arguments);
    },

    set_oto_pos_quotation_form(formId, partnerId, receiptInfo) {
        this.oto_pos_quotation_form_id = formId || false;
        this.oto_pos_quotation_form_partner_id = formId ? partnerId || false : false;
        this.oto_pos_receipt_info = formId ? receiptInfo || this.oto_pos_receipt_info || {} : {};
        this.trigger("change", this);
    },
});

FormController.include({
    _onSave(event) {
        if (this.modelName !== "oto.pos.quotation.form") {
            return this._super.apply(this, arguments);
        }

        event.stopPropagation();
        this._disableButtons();
        return this.saveRecord()
            .then(() => {
                const formId = this.getSelectedIds()[0] || false;
                this._enableButtons();
                return this.do_action({
                    type: "ir.actions.act_window_close",
                    infos: { oto_pos_quotation_form_id: formId },
                });
            })
            .guardedCatch(this._enableButtons.bind(this));
    },
});

const OtoPosCustomerClientListScreen = (ClientListScreen) =>
    class extends ClientListScreen {
        async editClient() {
            if (!this.state.selectedClient) {
                return;
            }
            await this._openPartnerForm(this.state.selectedClient.id);
        }

        async activateEditMode(event) {
            const partnerId = event.detail.isNewClient
                ? false
                : this.state.selectedClient && this.state.selectedClient.id;
            await this._openPartnerForm(partnerId);
        }

        confirm() {
            document.body.classList.remove(CUSTOMER_FORM_OPEN_CLASS);
            const selectedClient = this.state.selectedClient;
            if (
                this._pendingQuotationFormId &&
                selectedClient &&
                selectedClient.id === this._pendingQuotationFormPartnerId
            ) {
                this.currentOrder.set_oto_pos_quotation_form(
                    this._pendingQuotationFormId,
                    this._pendingQuotationFormPartnerId,
                    this._pendingQuotationReceiptInfo
                );
            } else if (this._pendingQuotationFormId) {
                this.currentOrder.set_oto_pos_quotation_form(false, false);
            }
            return super.confirm(...arguments);
        }

        back() {
            document.body.classList.remove(CUSTOMER_FORM_OPEN_CLASS);
            return super.back(...arguments);
        }

        async _openPartnerForm(partnerId) {
            if (this._openingPartnerForm) {
                return;
            }
            this._openingPartnerForm = true;
            try {
                const action = await this.rpc({
                    model: "res.partner",
                    method: "oto_pos_customer_form_action",
                    args: [partnerId || false],
                });
                document.body.classList.add(CUSTOMER_FORM_OPEN_CLASS);
                await this.env.pos.do_action(action, {
                    on_close: (closeInfo) => {
                        document.body.classList.remove(CUSTOMER_FORM_OPEN_CLASS);
                        const formId = closeInfo && closeInfo.oto_pos_quotation_form_id;
                        return this._syncPartnerAfterForm(formId);
                    },
                });
                const form = document.querySelector(".oto_pos_quotation_form");
                const dialog = form && form.closest(".modal-dialog");
                if (dialog) {
                    dialog.classList.add(CUSTOMER_FORM_DIALOG_CLASS);
                }
            } catch (error) {
                document.body.classList.remove(CUSTOMER_FORM_OPEN_CLASS);
                if (isConnectionError(error)) {
                    await this.showPopup("OfflineErrorPopup", {
                        title: this.env._t("Offline"),
                        body: this.env._t("Customer form needs an online connection."),
                    });
                } else {
                    throw error;
                }
            } finally {
                this._openingPartnerForm = false;
            }
        }

        async _syncPartnerAfterForm(formId) {
            if (!formId) {
                return;
            }
            try {
                const receiptInfo = await this.rpc({
                    model: "oto.pos.quotation.form",
                    method: "oto_pos_receipt_info",
                    args: [formId],
                });
                const partnerId = receiptInfo && receiptInfo.partner_id;
                if (!partnerId) {
                    return;
                }
                await this.env.pos._loadPartners([partnerId]);
                const partner = this.env.pos.db.get_partner_by_id(partnerId);
                if (partner) {
                    this._pendingQuotationFormId = formId;
                    this._pendingQuotationFormPartnerId = partnerId;
                    this._pendingQuotationReceiptInfo = receiptInfo;
                    const currentClient = this.currentOrder.get_client();
                    if (currentClient && currentClient.id === partnerId) {
                        this.currentOrder.set_oto_pos_quotation_form(formId, partnerId, receiptInfo);
                    }
                    this.state.selectedClient = partner;
                    this.state.detailIsShown = false;
                    this.state.isEditMode = false;
                    this.render();
                }
            } catch (error) {
                if (!isConnectionError(error)) {
                    throw error;
                }
            }
        }
    };

Registries.Component.extend(ClientListScreen, OtoPosCustomerClientListScreen);

return ClientListScreen;
});
