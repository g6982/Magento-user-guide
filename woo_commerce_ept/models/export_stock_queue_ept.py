import ast
import logging
import pytz
from odoo import models, fields, api, _

utc = pytz.utc

_logger = logging.getLogger("Woo Commerce Export Stock Queue")


class WooExportStockQueueEpt(models.Model):
    _name = "woo.export.stock.queue.ept"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Woo Commerce Export Stock Queue"

    name = fields.Char(size=120)
    woo_instance_id = fields.Many2one("woo.instance.ept", string="Instance")
    state = fields.Selection([("draft", "Draft"), ("partially_completed", "Partially Completed"),
                              ("completed", "Completed"), ("failed", "Failed")], default="draft",
                             compute="_compute_queue_state", store=True, tracking=True)
    export_stock_queue_line_ids = fields.One2many("woo.export.stock.queue.line.ept",
                                                  "export_stock_queue_id",
                                                  string="Export Stock Queue Lines")
    common_log_book_id = fields.Many2one("common.log.book.ept",
                                         help="""Related Log book which has all logs for current queue.""")
    common_log_lines_ids = fields.One2many(related="common_log_book_id.log_lines")
    queue_line_total_records = fields.Integer(string="Total Records",
                                              compute="_compute_queue_line_record")
    queue_line_draft_records = fields.Integer(string="Draft Records",
                                              compute="_compute_queue_line_record")
    queue_line_fail_records = fields.Integer(string="Fail Records",
                                             compute="_compute_queue_line_record")
    queue_line_done_records = fields.Integer(string="Done Records",
                                             compute="_compute_queue_line_record")
    queue_line_cancel_records = fields.Integer(string="Cancelled Records",
                                               compute="_compute_queue_line_record")
    created_by = fields.Selection([("import", "By Import Process"), ("webhook", "By Webhook")],
                                  help="Identify the process that generated a queue.",
                                  default="import")
    is_process_queue = fields.Boolean("Is Processing Queue", default=False)
    running_status = fields.Char(default="Running...")
    is_action_require = fields.Boolean(default=False)
    queue_process_count = fields.Integer(string="Queue Process Times",
                                         help="it is used know queue how many time processed")

    @api.depends("export_stock_queue_line_ids.state")
    def _compute_queue_line_record(self):
        """This is used for count of total record of export_stock queue line base on it's state and
        it display in the form view of export stock queue.
        @author: Nilam Kubavat @Emipro Technologies Pvt.Ltd on date 31-Aug-2022.
        Task Id : 199065
        """
        for export_stock_queue in self:
            queue_lines = export_stock_queue.export_stock_queue_line_ids
            export_stock_queue.queue_line_total_records = len(queue_lines)
            export_stock_queue.queue_line_draft_records = len(queue_lines.filtered(lambda x: x.state == "draft"))
            export_stock_queue.queue_line_fail_records = len(queue_lines.filtered(lambda x: x.state == "failed"))
            export_stock_queue.queue_line_done_records = len(queue_lines.filtered(lambda x: x.state == "done"))
            export_stock_queue.queue_line_cancel_records = len(queue_lines.filtered(lambda x: x.state == "cancel"))

    @api.depends("export_stock_queue_line_ids.state")
    def _compute_queue_state(self):
        """
        Computes queue state from different states of queue lines.
        @author: Nilam Kubavat @Emipro Technologies Pvt.Ltd on date 31-Aug-2022.
        Task Id : 199065
        """
        for record in self:
            if record.queue_line_total_records == record.queue_line_done_records + record.queue_line_cancel_records:
                record.state = "completed"
            elif record.queue_line_draft_records == record.queue_line_total_records:
                record.state = "draft"
            elif record.queue_line_total_records == record.queue_line_fail_records:
                record.state = "failed"
            else:
                record.state = "partially_completed"

    @api.model
    def create(self, vals):
        """This method used to create a sequence for export_stock queue.
           @author: Nilam Kubavat @Emipro Technologies Pvt.Ltd on date 31-Aug-2022.
        Task Id : 199065
        """
        sequence_id = self.env.ref("woo_commerce_ept.seq_export_stock_queue").ids
        if sequence_id:
            record_name = self.env["ir.sequence"].browse(sequence_id).next_by_id()
        else:
            record_name = "/"
        vals.update({"name": record_name or ""})
        return super(WooExportStockQueueEpt, self).create(vals)

    def create_woo_export_stock_queue(self, instance, exprot_stock_data):
        """
        Creates export stock queues and adds queue lines in it.
        @author: Nilam Kubavat @Emipro Technologies Pvt.Ltd on date 31-Aug-2022.
        Task Id : 199065
        """
        count = 50
        export_stock_queue = []
        for data in exprot_stock_data:
            if count == 50:
                count = 0
                queue_id = self.woo_create_export_stock_queue(instance)
                export_stock_queue.append(queue_id.id)
                message = "Export Stock Queue Created", queue_id.name
                self._cr.commit()
                _logger.info(message)
            self.woo_create_export_stock_queue_line(data, instance, queue_id)
            count += 1
        if queue_id.export_stock_queue_line_ids:
            self.env["bus.bus"]._sendone(self.env.user.partner_id, 'simple_notification',
                                         {"title": "WooCommerce Connector",
                                          "message": message, "sticky": False, "warning": True})
            self._cr.commit()
        return export_stock_queue

    def woo_create_export_stock_queue(self, instance):
        """
        This method used to create a product queue.
        @author: Nilam Kubavat @Emipro Technologies Pvt.Ltd on date 31-Aug-2022.
        Task Id : 199065
        """
        product_queue_vals = {
            "woo_instance_id": instance and instance.id or False
        }
        return self.create(product_queue_vals)

    def woo_create_export_stock_queue_line(self, data, instance, export_stock_queue):
        """
        This method used to create a export stock data queue line.
        @author: Nilam Kubavat @Emipro Technologies Pvt.Ltd on date 31-Aug-2022.
        Task Id : 199065
        """
        export_stock_queue_line_vals = {
            "woo_instance_id": instance and instance.id or False,
            "batch_details": data.get('batch_details'),
            "woo_tmpl_id": data.get('woo_tmpl_id'),
            "product_type": data.get('product_type'),
            "export_stock_queue_id": export_stock_queue and export_stock_queue.id or False
        }
        self.env['woo.export.stock.queue.line.ept'].create(export_stock_queue_line_vals)
        return True

    @api.model
    def retrieve_dashboard(self, *args, **kwargs):
        dashboard = self.env['queue.line.dashboard']
        return dashboard.get_data(table='woo.export.stock.queue.line.ept')
