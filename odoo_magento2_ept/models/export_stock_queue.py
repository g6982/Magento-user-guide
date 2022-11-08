from odoo import models, fields, api


class MagentoExportStockQueueEpt(models.Model):
    """
    Describes Magento Export Stock Queue
    """
    _name = "magento.export.stock.queue.ept"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Magento Export Stock Queue"

    name = fields.Char(help="Sequential name of Export Stock.", copy=False)
    instance_id = fields.Many2one(comodel_name='magento.instance',
                                  string='Magento Instance',
                                  help="Export stock from this Magento Instance.")
    state = fields.Selection([('draft', 'Draft'),
                              ('partially_completed', 'Partially Completed'),
                              ('completed', 'Completed'), ('failed', 'Failed')],
                             default='draft',
                             copy=False, compute="_compute_queue_state",
                             store=True, help="Status of Export Stock Data Queue", )
    log_book_id = fields.Many2one(comodel_name="common.log.book.ept",
                                  help="Related Log book which has all logs for current queue.")
    log_lines_ids = fields.One2many(related="log_book_id.log_lines",
                                    help="Log lines of Common log book for particular Export Stock queue")

    line_ids = fields.One2many("magento.export.stock.queue.line.ept", "queue_id",
                               help="Export Stock data queue line ids")
    total_count = fields.Integer(string='Total Records',
                                 compute='_compute_record',
                                 help="Returns total number of export stock data queue lines")
    draft_count = fields.Integer(string='Draft Records',
                                 compute='_compute_record',
                                 help="Returns total number of draft export stock data queue lines")
    failed_count = fields.Integer(string='Fail Records',
                                  compute='_compute_record',
                                  help="Returns total number of Failed export stock data queue lines")
    done_count = fields.Integer(string='Done Records',
                                compute='_compute_record',
                                help="Returns total number of done export stock data queue lines")
    cancel_count = fields.Integer(string='Cancel Records',
                                  compute='_compute_record',
                                  help="Returns total number of cancel export stock data queue lines")
    is_process_queue = fields.Boolean('Is Processing Queue', default=False)
    running_status = fields.Char(default="Running...")
    is_action_require = fields.Boolean(default=False)
    process_count = fields.Integer(string="Queue Process Times", default=0,
                                   help="It is used know queue how many time processed")

    def create_export_stock_queues(self, instance, data):
        queue = self._create_export_stock_queue(instance)
        if len(queue.line_ids) == 50:
            self._cr.commit()
            queue = self._create_export_stock_queue(instance)
        self.line_ids.create_export_stock_queue_line(instance, data, queue)

    def _create_export_stock_queue(self, instance):
        """
        Creates Export Stock queue
        :param instance: Instance of Magento
        :return: Magento Export Stock Data queue object
        """
        queue = self.search([('instance_id', '=', instance.id), ('state', '=', 'draft')])
        queue = queue.filtered(lambda q: len(q.line_ids) < 50)
        if not queue:
            queue = self.create({'instance_id': instance.id})
            message = f"Export Stock Queue #{queue.name} Created!!"
            instance.show_popup_notification(message)
        return queue[0]

    def process_export_stock_queues(self, is_manual=False):
        for queue in self.filtered(lambda q: q.state not in ['completed', 'failed']):
            # To maintain that current queue has started to process.
            self._cr.commit()
            log = queue.log_book_id
            if not log:
                log = queue.instance_id.create_log_book(model=queue._name)
            queue.write({'is_process_queue': True, 'log_book_id': log.id})
            lines = queue.line_ids.filtered(lambda l: l.state == 'draft')
            queue.write({'process_count': queue.process_count + 1})
            if not is_manual and queue.process_count >= 3:
                note = f"Attention {queue.name} Customer Queue are processed 3 times and it failed. \n" \
                       f"You need to process it manually"
                queue.instance_id.create_schedule_activity(queue=queue, note=note)
                queue.write({'is_process_queue': False})
            if queue.instance_id.magento_version in ['2.1',
                                                     '2.2'] or not queue.instance_id.is_multi_warehouse_in_magento:
                # This condition is checked for verify the Magento version.
                # We only call this method for NON MSI magento versions. If customer using
                # Magento version 2.3+ and not using the MSI functionality then also this method
                # will be called.
                api_url = "/V1/product/updatestock"
            else:
                api_url = "/V1/inventory/source-items"

            lines.process_export_stock_queue_line(api_url, log)
            message = "Export Stock Queue #{} Processed!!".format(queue.name)
            queue.instance_id.show_popup_notification(message)
            # To maintain that current queue process are completed and new queue will be executed.
            queue.write({'is_process_queue': False})
            self._cr.commit()
        return True

    @api.model
    def retrieve_dashboard(self, *args, **kwargs):
        dashboard = self.env['queue.line.dashboard']
        return dashboard.get_data(table='magento.export.stock.queue.line.ept')

    @api.depends('line_ids.state')
    def _compute_record(self):
        """
        This will calculate total, draft, failed and done orders from Magento.
        """
        for queue in self:
            queue.total_count = len(queue.line_ids)
            queue.draft_count = len(queue.line_ids.filtered(lambda x: x.state == 'draft'))
            queue.failed_count = len(queue.line_ids.filtered(lambda x: x.state == 'failed'))
            queue.done_count = len(queue.line_ids.filtered(lambda x: x.state == 'done'))
            queue.cancel_count = len(queue.line_ids.filtered(lambda x: x.state == 'cancel'))

    def create(self, vals):
        """
        Creates a sequence for Export Stock Queue
        :param vals: values to create Export Stock Queue
        :return: MagentoExportStockQueueEpt Object
        """
        sequence_id = self.env.ref('odoo_magento2_ept.seq_customer_queue_data').ids
        if sequence_id:
            record_name = self.env['ir.sequence'].browse(sequence_id).next_by_id()
        else:
            record_name = '/'
        vals.update({'name': record_name or ''})
        return super(MagentoExportStockQueueEpt, self).create(vals)

    @api.depends('line_ids.state')
    def _compute_queue_state(self):
        """
        Computes state from different states of queue lines.
        """
        for record in self:
            if record.total_count == record.done_count + record.cancel_count:
                record.state = "completed"
            elif record.total_count == record.draft_count:
                record.state = "draft"
            elif record.total_count == record.failed_count:
                if record.state != "failed":
                    record.state = "failed"
                    note = f"Attention {record.name} Customer Queue is failed. \n" \
                           f"You need to process it manually."
                    self.env['magento.instance'].create_activity(model_name=self._name,
                                                                 res_id=record.id,
                                                                 message=note,
                                                                 summary=self.name,
                                                                 instance=record.instance_id)
            else:
                record.state = "partially_completed"
