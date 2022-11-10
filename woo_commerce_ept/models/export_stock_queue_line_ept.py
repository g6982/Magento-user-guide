import ast
import time
from odoo.exceptions import UserError
import logging
from datetime import datetime
import pytz
from odoo import models, fields, api, _

utc = pytz.utc

_logger = logging.getLogger("Woo Commerce Export Stock Queue Line")


class WooOrderDataQueueLineEpt(models.Model):
    _name = "woo.export.stock.queue.line.ept"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Woo Commerce Export Stock Queue Line"

    name = fields.Char(size=120)
    woo_instance_id = fields.Many2one("woo.instance.ept", string="Instance")
    last_process_date = fields.Datetime()
    batch_details = fields.Char()
    woo_tmpl_id = fields.Char()
    product_type = fields.Selection([('simple', 'Simple'), ('variable', 'Variable')])
    state = fields.Selection([("draft", "Draft"), ("failed", "Failed"), ("done", "Done"),
                              ("cancel", "Cancelled")],
                             default="draft")
    export_stock_queue_id = fields.Many2one("woo.export.stock.queue.ept", required=True,
                                            ondelete="cascade", copy=False)
    common_log_lines_ids = fields.One2many("common.log.lines.ept",
                                           "woo_export_stock_queue_line_id",
                                           help="Log lines created against which line.")

    def auto_export_stock_queue_data(self):
        """
        This method is used to find export stock queue which queue lines have state in draft and is_action_require is False.
        @author: Nilam Kubavat @Emipro Technologies Pvt.Ltd on date 31-Aug-2022.
        Task Id : 199065
        """
        export_stock_queue_obj = self.env["woo.export.stock.queue.ept"]
        export_stock_queue_ids = []

        self.env.cr.execute(
            """update woo_export_stock_queue_ept set is_process_queue = False where is_process_queue = True""")
        self._cr.commit()

        query = """select queue.id
                from woo_export_stock_queue_line_ept as queue_line  
                inner join woo_export_stock_queue_ept as queue on queue_line.export_stock_queue_id = queue.id
                where queue_line.state in ('draft') and queue.is_action_require = 'False'
                ORDER BY queue_line.create_date ASC"""
        self._cr.execute(query)
        export_stock_queue_list = self._cr.fetchall()
        if not export_stock_queue_list:
            return True

        for result in export_stock_queue_list:
            if result[0] not in export_stock_queue_list:
                export_stock_queue_ids.append(result[0])

        queues = export_stock_queue_obj.browse(export_stock_queue_ids)
        self.filter_export_stock_queue_lines_and_post_message(queues)
        return True

    def filter_export_stock_queue_lines_and_post_message(self, queues):
        """
        This method is used to post a message if the queue is process more than 3 times otherwise
        it calls the child method to process the export stock queue line.
        @author: Nilam Kubavat @Emipro Technologies Pvt.Ltd on date 31-Aug-2022.
        Task Id : 199065
        """
        ir_model_obj = self.env["ir.model"]
        common_log_book_obj = self.env["common.log.book.ept"]
        start = time.time()
        export_stock_queue_process_cron_time = queues.woo_instance_id.get_woo_cron_execution_time(
            "woo_commerce_ept.process_woo_export_stock_queue")

        for queue in queues:
            export_stock_queue_line_ids = queue.export_stock_queue_line_ids.filtered(lambda x: x.state == "draft")

            queue.queue_process_count += 1
            if queue.queue_process_count > 3:
                queue.is_action_require = True
                note = "<p>Need to process this export stock queue manually.There are 3 attempts been made by " \
                       "automated action to process this queue,<br/>- Ignore, if this queue is already processed.</p>"
                queue.message_post(body=note)
                if queue.woo_instance_id.is_create_schedule_activity:
                    model_id = ir_model_obj.search([("model", "=", "woo.export.stock.queue.ept")])
                    common_log_book_obj.create_woo_schedule_activity(queue, model_id, True)
                continue

            self._cr.commit()
            export_stock_queue_line_ids.process_export_stock_queue_data()
            if time.time() - start > export_stock_queue_process_cron_time - 60:
                return True
        return True

    def process_export_stock_queue_data(self):
        """
        This method is used to processes export stock queue lines.
        @author: Nilam Kubavat @Emipro Technologies Pvt.Ltd on date 31-Aug-2022.
        Task Id : 199065
        """
        common_log_book_obj = self.env["common.log.book.ept"]
        common_log_line_obj = self.env['common.log.lines.ept']
        model_id = common_log_book_obj.log_lines.get_model_id("woo.export.stock.queue.ept")
        queue_id = self.export_stock_queue_id if len(self.export_stock_queue_id) == 1 else False
        log_book_id = queue_id.common_log_book_id
        if queue_id:
            instance = queue_id.woo_instance_id
            if not queue_id.common_log_book_id:
                log_book_id = common_log_book_obj.woo_create_log_book("export", instance)
                queue_id.write({'common_log_book_id': log_book_id})
            self.env.cr.execute(
                """update woo_product_data_queue_ept set is_process_queue = False where is_process_queue = True""")
            self._cr.commit()
            wc_api = instance.woo_connect()
            for queue_line in self:
                _logger.info('Starting Batch Products Stock Update Process.')
                batch_details = ast.literal_eval(queue_line.batch_details)
                try:
                    if queue_line.product_type == 'simple':
                        res = wc_api.post('products/batch', {'update': batch_details})
                    if queue_line.product_type == 'variable':
                        for batch in batch_details:
                            res = wc_api.post('products/%s/variations/batch' % queue_line.woo_tmpl_id,
                                              {'update': batch})
                    if res.status_code == 200:
                        queue_id.is_process_queue = True
                        queue_line.write({"state": "done"})
                    else:
                        queue_line.write({"state": "failed"})
                except Exception as error:
                    raise UserError(
                        _("Something went wrong while Exporting Stock.\n\nPlease Check your Connection and "
                          "Instance Configuration.\n\n" + str(error)))
                _logger.info('Completed Product Batch Stock Update Process Completed with [Status: %s]',
                             res.status_code)
                response = self.env["woo.product.template.ept"].check_woocommerce_response(res,
                                                                                           "Update Product Stock",
                                                                                           model_id)
                if not isinstance(response, dict):
                    continue
                if response.get('data', {}) and response.get('data', {}).get('status') != 200:
                    message = "Update Product \n%s" % (response.get('message'))
                    common_log_line_obj.woo_product_export_log_line(message, model_id, log_book_id, False)
                    continue
            self._cr.commit()
        if not log_book_id.log_lines:
            log_book_id.unlink()
        else:
            queue_id.common_log_book_id = log_book_id
            if queue_id.woo_instance_id.is_create_schedule_activity:
                log_book_id.create_woo_schedule_activity()

        return True
