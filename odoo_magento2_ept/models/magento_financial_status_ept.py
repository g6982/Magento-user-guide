# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class MagentoFinancialStatusEpt(models.Model):
    _name = "magento.financial.status.ept"
    _description = 'Magento Financial Status'

    def _default_payment_term(self):
        payment_term = self.env.ref("account.account_payment_term_immediate")
        return payment_term.id if payment_term else False

    financial_status = fields.Selection([('not_paid', 'Pending Orders'),
                                         ('processing_paid', 'Processing orders with Invoice'),
                                         ('processing_unpaid', 'Processing orders with Shipping'),
                                         ('paid', 'Completed orders'),
                                         ], default="not_paid")
    auto_workflow_id = fields.Many2one("sale.workflow.process.ept", "Auto Workflow",
                                       ondelete="restrict")
    payment_method_id = fields.Many2one("magento.payment.method", "Payment Gateway",
                                        ondelete="restrict")
    payment_term_id = fields.Many2one(
        'account.payment.term', string='Payment Term', default=_default_payment_term,
        ondelete="restrict")
    magento_instance_id = fields.Many2one(
        "magento.instance", string="Instance", ondelete="cascade",
        help="This field relocates magento instance")
    active = fields.Boolean("Active Financial Status", default=True)

    _sql_constraints = [('_magento_workflow_unique_constraint',
                         'unique(financial_status,magento_instance_id,payment_method_id)',
                         "Financial status must be unique in the list")]

    def create_financial_status(self, magento_instance, financial_status):
        """
        Creates Financial Status for the payment methods of the Instance.
        :param magento_instance: Magento Instance
        :param financial_status: Financial Status can be pending, processing_paid, processing_unpaid or paid.
        :return: True
        """
        payment_methods = self.env['magento.payment.method'].search(
            [('magento_instance_id', '=', magento_instance.id)])
        for payment_method in payment_methods:
            domain = [('magento_instance_id', '=', magento_instance.id),
                      ('payment_method_id', '=', payment_method.id),
                      ('financial_status', '=', financial_status)]
            existing_financial_status = self.search(domain).ids
            if existing_financial_status:
                continue
            if payment_method.magento_workflow_process_id:
                workflow = payment_method.magento_workflow_process_id
            else:
                workflow = self.env.ref("common_connector_library.automatic_validation_ept")
            if payment_method.payment_term_id:
                payment_term_id = payment_method.payment_term_id
            else:
                payment_term_id = self.env.ref("account.account_payment_term_immediate")
            self.create({
                'magento_instance_id': magento_instance.id,
                'auto_workflow_id': workflow.id,
                'payment_method_id': payment_method.id,
                'financial_status': financial_status,
                'payment_term_id': payment_term_id.id
            })
        return True

    @staticmethod
    def __get_status_code(order_status, is_invoice, is_shipment):
        """
        Get Financial Status Dictionary.
        :param order_status: Order status received from Magento.
        :param is_invoice: Order is invoiced.
        :param is_shipment: Order is Shipped.
        :return: Financial Status dictionary
        """
        status_code = ''
        if order_status == "pending":
            status_code = 'not_paid'
        elif order_status == "processing" and is_invoice and not is_shipment:
            status_code = 'processing_paid'
        elif order_status == "processing" and is_shipment and not is_invoice:
            status_code = 'processing_unpaid'
        elif order_status == "complete":
            status_code = 'paid'
        return status_code

    @staticmethod
    def __get_status_name(order_status, is_invoice, is_shipment):
        """
        Get Financial Status Dictionary.
        :param order_status: Order status received from Magento.
        :param is_invoice: Order is invoiced.
        :param is_shipment: Order is Shipped.
        :return: Financial Status dictionary
        """
        status_name = ''
        if order_status == "pending":
            status_name = 'Pending Orders'
        elif order_status == "processing" and is_invoice and not is_shipment:
            status_name = 'Processing orders with Invoice'
        elif order_status == "processing" and is_shipment and not is_invoice:
            status_name = 'Processing orders with Shipping'
        elif order_status == "complete":
            status_name = 'Completed Orders'
        return status_name

    def search_financial_status(self, order_response, magento_instance, payment_option):
        """
        Search order Financial status.
        :param order_response: Response received from Magento.
        :param magento_instance: Magento Instance.
        :param payment_option: Magento Order Payment Method
        :return: Financial Status object, Financial Status Name
        """
        order_status_ojb = self.env['magento.order.status.ept']
        mapped_order_status = order_status_ojb.search([('magento_instance_id', '=', magento_instance.id),
                  ('m_order_status_code', '=', order_response.get('status'))])

        is_invoice = order_response.get('extension_attributes').get('is_invoice')
        is_shipment = order_response.get('extension_attributes').get('is_shipment')
        status_name = self.__get_status_name(mapped_order_status.main_status, is_invoice, is_shipment)
        status_code = self.__get_status_code(mapped_order_status.main_status, is_invoice, is_shipment)
        workflow_config = self.env['magento.financial.status.ept'].search(
            [('magento_instance_id', '=', magento_instance.id),
             ('payment_method_id', '=', payment_option.id),
             ('financial_status', '=', status_code)])
        return {'workflow': workflow_config, 'status_name': status_name}
