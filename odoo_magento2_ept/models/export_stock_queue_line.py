import json
from datetime import datetime
from odoo import models, fields


class MagentoExportStockLineEpt(models.Model):
    """
    Describes Export Stock Data Queue Line
    """
    _name = "magento.export.stock.queue.line.ept"
    _description = "Magento Export Stock Queue Line"

    queue_id = fields.Many2one(comodel_name='magento.export.stock.queue.ept', ondelete="cascade")
    instance_id = fields.Many2one(comodel_name='magento.instance',
                                  string='Magento Instance',
                                  help="Export Stock from this Magento Instance.")
    state = fields.Selection([("draft", "Draft"), ("failed", "Failed"),
                              ("done", "Done"), ("cancel", "Cancelled")], default="draft",
                             copy=False)
    data = fields.Text(string="Data", copy=False,
                       help="Data imported from Magento of current customer.")
    processed_at = fields.Datetime(string="Process Time", copy=False,
                                   help="Shows Date and Time, When the data is processed")
    log_lines_ids = fields.One2many("common.log.lines.ept", "magento_export_stock_queue_line_id",
                                    help="Log lines created against which line.")

    def create_export_stock_queue_line(self, instance, data, queue):
        """
        :param instance: Instance object
        :param data: Stock data
        :param queue: Queue object
        """
        self.create({
            'instance_id': instance.id,
            'data': json.dumps(data),
            'queue_id': queue.id,
            'state': 'draft',
        })
        return True

    def auto_process_export_stock_queues(self):
        """
        Cron execute time run this method.
        :return: True
        """
        queues = self.instance_id.get_draft_queues(model='magento_export_stock_queue_line_ept',
                                                   name=self.queue_id._name)
        queues.process_export_stock_queues()
        return True

    def process_export_stock_queue_line(self, api_url, log):
        """
        :param api_url: Export stock url MSI or Non MSI
        :param log: Log object
        :return: True
        """
        magento_product = self.env['magento.product.product']
        for line in self:
            is_processed = magento_product.export_magento_stock(line, api_url, log)
            if is_processed:
                line.write({'state': 'done', 'processed_at': datetime.now()})
            else:
                line.write({'state': 'failed', 'processed_at': datetime.now()})
            self._cr.commit()
        return True
