# See LICENSE file for full copyright and licensing details.
"""
Describes Wizard for processing order queue
"""
from odoo import models, api, _


class MagentoQueueProcessEpt(models.TransientModel):
    """
    Describes Wizard for processing order queue
    """
    _name = 'magento.queue.process.ept'
    _description = 'Magento Queue Process Ept'

    def manual_queue_process(self):
        """
        Process order manually
        """
        queue_process = self._context.get('queue_process')
        if queue_process == "process_order_queue_manually":
            queue = self.env['magento.order.data.queue.ept']
            queues = queue.browse(self._context.get('active_ids'))
            queues.process_order_queues(is_manual=True)
        if queue_process == "process_product_queue_manually":
            queue = self.env['sync.import.magento.product.queue']
            queues = queue.browse(self._context.get('active_ids'))
            queues.process_product_queues(is_manual=True)
        if queue_process == "process_customer_queue_manually":
            queue = self.env['magento.customer.data.queue.ept']
            queues = queue.browse(self._context.get('active_ids'))
            queues.process_customer_queues(is_manual=True)
        if queue_process == "process_export_stock_queue_manually":
            queue = self.env['magento.export.stock.queue.ept']
            queues = queue.browse(self._context.get('active_ids'))
            queues.process_export_stock_queues(is_manual=True)
        return True

    # @api.model
    # def process_order_queue_manually(self):
    #     """
    #     Process queued orders manually
    #     """
    #     order_queue_ids = self._context.get('active_ids')
    #     order_queue_ids = self.env['magento.order.data.queue.ept'].browse(order_queue_ids).filtered(
    #         lambda x: x.state != 'done')
    #     for order_queue_id in order_queue_ids:
    #         queue_lines = order_queue_id.order_data_queue_line_ids.filtered(
    #             lambda line: line.state in ['draft', 'failed'])
    #         queue_lines.process_import_magento_order_queue_data()
    #     return True

    # @api.model
    # def process_product_queue_manually(self):
    #     """
    #     Process queued products manually
    #     """
    #     product_queue_ids = self._context.get('active_ids')
    #     product_queue_ids = self.env['sync.import.magento.product.queue'].\
    #         browse(product_queue_ids).filtered(lambda x: x.state != 'done')
    #     for product_queue_id in product_queue_ids:
    #         queue_lines = product_queue_id.line_ids.filtered(
    #             lambda line: line.state in ['draft', 'failed'])
    #         queue_lines.process_import_product_queue_data()
    #     return True

    @api.model
    def process_customer_queue_manually(self):
        """
        Process queued products manually
        """
        customer_queue_ids = self._context.get('active_ids')
        customer_queue_ids = self.env['magento.customer.data.queue.ept']. \
            browse(customer_queue_ids).filtered(lambda x: x.state != 'done')
        for customer_queue_id in customer_queue_ids:
            queue_lines = customer_queue_id.line_ids.filtered(
                lambda line: line.state in ['draft', 'failed'])
            queue_lines.process_import_customer_queue_data()
        return True

    def set_to_completed_queue(self):
        """
        This method is used to change the queue state as completed.
        """
        queue_process = self._context.get('queue_process')
        if queue_process == "set_to_completed_order_queue":
            self.set_to_completed_order_queue_manually()
        if queue_process == "set_to_completed_product_queue":
            self.set_to_completed_product_queue_manually()
        if queue_process == "set_to_completed_customer_queue":
            self.set_to_completed_customer_queue_manually()
        if queue_process == "set_to_completed_export_stock_queue":
            self.set_to_completed_export_stock_queue_manually()

    def set_to_completed_order_queue_manually(self):
        """
        This method is used to set order queue as completed. You can call the method from here:
        Magento => Logs => Orders => SET TO COMPLETED
        :return:
        """
        order_queue_ids = self._context.get('active_ids')
        order_queue_ids = self.env['magento.order.data.queue.ept'].browse(order_queue_ids).filtered(
            lambda x: x.state != 'done')
        self.env.cr.execute(
            """update magento_order_data_queue_ept set is_process_queue = False where is_process_queue = True""")
        self._cr.commit()
        for order_queue_id in order_queue_ids:
            queue_lines = order_queue_id.line_ids.filtered(
                lambda line: line.state in ['draft', 'failed'])
            queue_lines.write({'state': 'cancel'})
            order_queue_id.message_post(
                body=_("Manually set to cancel queue lines - %s ") % (queue_lines.mapped('magento_id')))
        return True

    def set_to_completed_product_queue_manually(self):
        """
        This method is used to set product queue as completed. You can call the method from here:
        Magento => Logs => Products => SET TO COMPLETED
        :return: True
        """
        product_queue_ids = self._context.get('active_ids')
        product_queue_ids = self.env['sync.import.magento.product.queue']. \
            browse(product_queue_ids).filtered(lambda x: x.state != 'done')
        self.env.cr.execute(
            """update sync_import_magento_product_queue set is_process_queue = False where is_process_queue = True""")
        self._cr.commit()
        for product_queue_id in product_queue_ids:
            queue_lines = product_queue_id.line_ids.filtered(
                lambda line: line.state in ['draft', 'failed'])
            queue_lines.write({'state': 'cancel'})
            product_queue_id.message_post(
                body=_("Manually set to cancel queue lines - %s ") % (queue_lines.mapped('product_sku')))
        return True

    def set_to_completed_customer_queue_manually(self):
        """
        This method is used to set order queue as completed. You can call the method from here:
        Magento => Logs => Orders => SET TO COMPLETED
        :return:
        """
        customer_queue_ids = self._context.get('active_ids')
        customer_queue_ids = self.env['magento.customer.data.queue.ept'].browse(customer_queue_ids).filtered(
            lambda x: x.state != 'done')
        self.env.cr.execute(
            """update magento_customer_data_queue_ept set is_process_queue = False where is_process_queue = True""")
        self._cr.commit()
        for customer_queue_id in customer_queue_ids:
            queue_lines = customer_queue_id.line_ids.filtered(
                lambda line: line.state in ['draft', 'failed'])
            queue_lines.write({'state': 'cancel'})
            customer_queue_id.message_post(
                body=_("Manually set to cancel queue lines - %s ") % (queue_lines.mapped('magento_id')))
        return True

    def set_to_completed_export_stock_queue_manually(self):
        """
        This method is used to set export stock queue as completed. You can call the method from here:
        Magento => Logs => Export Stock Queue => SET TO COMPLETED
        """
        export_stock_queue_ids = self._context.get('active_ids')
        export_stock_queue_ids = self.env['magento.export.stock.queue.ept'].browse(export_stock_queue_ids).filtered(
            lambda x: x.state != 'done')
        self.env.cr.execute(
            """update magento_export_stock_queue_ept set is_process_queue = False where is_process_queue = True""")
        self._cr.commit()
        for export_stock_queue_id in export_stock_queue_ids:
            queue_lines = export_stock_queue_id.line_ids.filtered(
                lambda line: line.state in ['draft', 'failed'])
            queue_lines.write({'state': 'cancel'})
            export_stock_queue_id.message_post(
                body=_("Manually set to cancel queue lines"))
        return True

    def magento_action_archive(self):
        """
        This method is used to call a child of the instance to active/inactive instance and its data.
        """
        instance_obj = self.env['magento.instance']
        instances = instance_obj.browse(self._context.get('active_ids'))
        for instance in instances:
            instance.magento_action_archive_unarchive()
