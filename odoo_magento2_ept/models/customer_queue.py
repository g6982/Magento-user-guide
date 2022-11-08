# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for Magento import customer data queue.
"""
import math
from datetime import datetime
from odoo import models, fields, api
from .api_request import req, create_search_criteria
from ..python_library.php import Php

MAGENTO_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class MagentoCustomerQueueEpt(models.Model):
    """
    Describes Magento Customer Data Queue
    """
    _name = "magento.customer.data.queue.ept"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Magento Customer Data Queue EPT"

    name = fields.Char(help="Sequential name of imported customer.", copy=False)
    instance_id = fields.Many2one(comodel_name='magento.instance',
                                  string='Magento Instance',
                                  help="Customer imported from this Magento Instance.")
    state = fields.Selection([('draft', 'Draft'),
                              ('partially_completed', 'Partially Completed'),
                              ('completed', 'Completed'), ('failed', 'Failed')],
                             default='draft',
                             copy=False, compute="_compute_queue_state",
                             store=True, help="Status of Customer Data Queue", )
    log_book_id = fields.Many2one(comodel_name="common.log.book.ept",
                                  help="Related Log book which has all logs for current queue.")
    log_lines_ids = fields.One2many(related="log_book_id.log_lines",
                                    help="Log lines of Common log book for particular customer queue")

    line_ids = fields.One2many("magento.customer.data.queue.line.ept", "queue_id",
                               help="Customer data queue line ids")
    total_count = fields.Integer(string='Total Records',
                                 compute='_compute_record',
                                 help="Returns total number of order data queue lines")
    draft_count = fields.Integer(string='Draft Records',
                                 compute='_compute_record',
                                 help="Returns total number of draft order data queue lines")
    failed_count = fields.Integer(string='Fail Records',
                                  compute='_compute_record',
                                  help="Returns total number of Failed order data queue lines")
    done_count = fields.Integer(string='Done Records',
                                compute='_compute_record',
                                help="Returns total number of done order data queue lines")
    cancel_count = fields.Integer(string='Cancel Records',
                                  compute='_compute_record',
                                  help="Returns total number of cancel order data queue lines")
    is_process_queue = fields.Boolean('Is Processing Queue', default=False)
    running_status = fields.Char(default="Running...")
    is_action_require = fields.Boolean(default=False)
    process_count = fields.Integer(string="Queue Process Times", default=0,
                                   help="It is used know queue how many time processed")

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
        Creates a sequence for Customer Data Queue
        :param vals: values to create Customer Data Queue
        :return: MagentoCustomerDataQueueEpt Object
        """
        sequence_id = self.env.ref('odoo_magento2_ept.seq_customer_queue_data').ids
        if sequence_id:
            record_name = self.env['ir.sequence'].browse(sequence_id).next_by_id()
        else:
            record_name = '/'
        vals.update({'name': record_name or ''})
        return super(MagentoCustomerQueueEpt, self).create(vals)

    def _create_customer_queue(self, instance):
        """
        Creates Imported Magento Customer queue
        :param instance: Instance of Magento
        :return: Magento Customer Data queue object
        """
        queue = self.search([('instance_id', '=', instance.id), ('state', '=', 'draft')])
        queue = queue.filtered(lambda q: len(q.line_ids) < 50)
        if not queue:
            queue = self.create({'instance_id': instance.id})
            message = f"Customer Queue #{queue.name} Created!!"
            instance.show_popup_notification(message)
        return queue[0]

    def create_customer_queues(self, **kwargs):
        """
        Import magento customers and stores them as a bunch of 50 orders queue
        :param instance: Instance of Magento
        """
        instance = kwargs.get('instance')
        page_size = 200
        queue_ids = []
        for website in instance.magento_website_ids:
            kwargs.update({'website': website, 'fields': ['total_count']})
            filters = self._prepare_customer_filter(**kwargs)
            query_string = Php.http_build_query(filters)
            req_path = f'/V1/customers/search?{query_string}'
            customers = req(instance=instance, path=req_path, is_raise=True)
            page = math.ceil(customers.get('total_count', 1) / page_size)
            kwargs.pop('fields')
            for page in range(1, page + 1):
                kwargs.update({'page': page, 'page_size': page_size})
                filters = self._prepare_customer_filter(**kwargs)
                query_string = Php.http_build_query(filters)
                req_path = f'/V1/customers/search?{query_string}'
                customers = req(instance=instance, path=req_path, is_raise=True)
                queue = self._create_customer_queue(instance)
                if queue.id not in queue_ids:
                    # Ids are prepared for return the customer to queue line tree view with created
                    # queue filters.
                    queue_ids.append(queue.id)
                for customer in customers.get('items'):
                    if len(queue.line_ids) == 50:
                        self._cr.commit()
                        queue = self._create_customer_queue(instance)
                    self.line_ids.create_queue_line(instance, customer, queue)
                instance.write({'magento_import_customer_current_page': page})
        return queue_ids

    @staticmethod
    def _prepare_customer_filter(**kwargs):
        """
        Create dictionary for required filters params for search customers from API.
        :param website: magento.website()
        :param kwargs: dict()
        :return: dict()
        """
        # Find last import date from magento instance if not found then pass None in from_date.
        # last_partner_import_date = kwargs.get('magento_instance').last_partner_import_date
        # if not last_partner_import_date:
        last_import = None
        to_date = datetime.now()
        if kwargs.get('from_date', False):
            last_import = kwargs.get('from_date').strftime(MAGENTO_DATETIME_FORMAT)
        if kwargs.get('to_date', False):
            to_date = kwargs.get('to_date', None).strftime(MAGENTO_DATETIME_FORMAT)
        filters = {
            'updated_at': {
                'from': last_import,
                'to': to_date
            },
            'website_id': {
                'in': kwargs.get('website').magento_website_id
            }
        }
        return create_search_criteria(filters, **kwargs)

    def process_customer_queues(self, is_manual=False):
        for queue in self.filtered(lambda q: q.state not in ['completed', 'failed']):
            # To maintain that current queue has started to process.
            queue.write({'is_process_queue': True})
            self._cr.commit()
            lines = queue.line_ids.filtered(lambda l: l.state in ('draft', 'cancel'))
            queue.write({'process_count': queue.process_count + 1})
            if not is_manual and queue.process_count >= 3:
                note = f"Attention {queue.name} Customer Queue are processed 3 times and it failed. \n" \
                       f"You need to process it manually"
                queue.instance_id.create_schedule_activity(queue=queue, note=note)
                queue.write({'is_process_queue': False})
            for line in lines:
                line.process_queue_line()
                line.write({'state': 'done'})
            message = "Customer Queue #{} Processed!!".format(queue.name)
            queue.instance_id.show_popup_notification(message)
            # To maintain that current queue process are completed and new queue will be executed.
            queue.write({'is_process_queue': False})
            self._cr.commit()
        return True

    @api.model
    def retrieve_dashboard(self, *args, **kwargs):
        dashboard = self.env['queue.line.dashboard']
        return dashboard.get_data(table='magento.customer.data.queue.line.ept')
