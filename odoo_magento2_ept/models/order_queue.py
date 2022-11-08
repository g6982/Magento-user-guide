# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for Magento import order data queue.
"""
import math
import time
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .api_request import req, create_search_criteria
from ..python_library.php import Php

MAGENTO_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class MagentoOrderDataQueueEpt(models.Model):
    """
    Describes Magento Order Data Queue
    """
    _name = "magento.order.data.queue.ept"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Magento Order Data Queue EPT"

    name = fields.Char(help="Sequential name of imported order.", copy=False)
    instance_id = fields.Many2one(
        'magento.instance', string='Magento Instance', help="Order imported from this Magento Instance.")
    state = fields.Selection([
        ('draft', 'Draft'), ('partially_completed', 'Partially Completed'),
        ('completed', 'Completed'), ('failed', 'Failed')
    ], default='draft', copy=False, help="Status of Order Data Queue", compute="_compute_queue_state", store=True)
    log_book_id = fields.Many2one(
        "common.log.book.ept", help="Related Log book which has all logs for current queue.")
    log_lines_ids = fields.One2many(
        related="log_book_id.log_lines", help="Log lines of Common log book for particular order queue")
    line_ids = fields.One2many(
        "magento.order.data.queue.line.ept", "queue_id", help="Order data queue line ids")
    total_count = fields.Integer(
        string='Total Records', compute='_compute_record',
        help="Returns total number of order data queue lines")
    draft_record = fields.Integer(
        string='Draft Records', compute='_compute_record',
        help="Returns total number of draft order data queue lines")
    failed_count = fields.Integer(
        string='Fail Records', compute='_compute_record',
        help="Returns total number of Failed order data queue lines")
    done_count = fields.Integer(
        string='Done Records', compute='_compute_record',
        help="Returns total number of done order data queue lines")
    cancel_count = fields.Integer(
        string='Cancel Records', compute='_compute_record',
        help="Returns total number of cancel order data queue lines")
    is_process_queue = fields.Boolean(string='Is Processing Queue', default=False)
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
            elif record.total_count == record.draft_record:
                record.state = "draft"
            elif record.total_count == record.failed_count:
                if record.state != "failed":
                    record.state = "failed"
                    note = "Attention {} Order Queue is failed. " \
                           "\nYou need to process it manually".format(record.name)
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
            queue.draft_record = len(queue.line_ids.filtered(lambda x: x.state == 'draft'))
            queue.failed_count = len(queue.line_ids.filtered(lambda x: x.state == 'failed'))
            queue.done_count = len(queue.line_ids.filtered(lambda x: x.state == 'done'))
            queue.cancel_count = len(queue.line_ids.filtered(lambda x: x.state == 'cancel'))

    def create(self, vals):
        """
        Creates a sequence for Ordered Data Queue
        :param vals: values to create Ordered Data Queue
        :return: MagentoOrderDataQueueEpt Object
        """
        sequence_id = self.env.ref('odoo_magento2_ept.seq_order_queue_data').ids
        if sequence_id:
            record_name = self.env['ir.sequence'].browse(sequence_id).next_by_id()
        else:
            record_name = '/'
        vals.update({'name': record_name or ''})
        return super(MagentoOrderDataQueueEpt, self).create(vals)

    def _create_order_queue(self, instance):
        """
        Creates Imported Magento orders queue
        :param instance: Instance of Magento
        :return: Magento order Data queue object
        """
        queue = self.search([('instance_id', '=', instance.id), ('state', '=', 'draft')])
        queue = queue.filtered(lambda q: len(q.line_ids) < 50)
        if not queue:
            queue = self.create({'instance_id': instance.id})
            message = "Order Queue #{} Created!!".format(queue.name)
            instance.show_popup_notification(message)
        return queue[0]

    def create_order_queues(self, **kwargs):
        queue_line = self.env['magento.order.data.queue.line.ept']
        instance = kwargs.get('instance')
        page_size = 200
        queue_ids = list()
        orders = self._get_order_response(instance, kwargs, True)
        page = math.ceil(orders.get('total_count', 1) / page_size)
        kwargs.pop('fields')
        if page == 0:
            if not kwargs.get('is_manual'):
                instance.write({'magento_import_order_page_count': 1})
            else:
                message = "No orders Found between {} and {} for {}".format(
                    datetime.strptime(kwargs.get('from_date'), '%Y-%m-%d %H:%M:%S').date(),
                    datetime.strptime(kwargs.get('to_date', None), '%Y-%m-%d %H:%M:%S').date(),
                    instance.name)
                instance.show_popup_notification(message)
        page = page if kwargs.get('is_manual') else instance.magento_import_order_page_count
        for page in range(1, page + 1):
            kwargs.update({'page': page, 'page_size': page_size})
            orders = self._get_order_response(instance, kwargs)
            if orders.get('items'):
                queue = self._create_order_queue(instance)
                queue_ids.append(queue.id)
                for order in orders.get('items'):
                    if len(queue.line_ids) == 50:
                        self._cr.commit()
                        queue = self._create_order_queue(instance)
                        queue_ids.append(queue.id)
                    queue_line.create_order_queue_line(instance, order, queue)
            instance.write({'magento_import_order_page_count': page})
        if not kwargs.get('is_manual'):
            instance.write({'magento_import_order_page_count': 1})
        return queue_ids

    def _get_order_response(self, instance, kwargs, get_pages=False):
        if get_pages:
            kwargs.update({'fields': ['total_count']})
        filters = self._prepare_order_filter(**kwargs)
        query_string = Php.http_build_query(filters)
        req_path = '/V1/orders?{}'.format(query_string)
        return req(instance, req_path, is_raise=True)

    @staticmethod
    def _prepare_order_filter(**kwargs):
        last_import = ''
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
            'state': {
                'in': kwargs.get('status')
            }
        }
        return create_search_criteria(filters, **kwargs)

    def import_specific_order(self, instance, order_reference_lists):
        """
        Creates order queues when import sale orders from Magento.
        :param instance: current instance of Magento
        :param order_reference_lists:  Dictionary of Order References
        :return:
        """
        queue_ids = list()
        queue_line = self.env['magento.order.data.queue.line.ept']
        for order_reference in order_reference_lists:
            filters = {'increment_id': order_reference}
            search_criteria = create_search_criteria(filters)
            query_string = Php.http_build_query(search_criteria)
            try:
                api_url = '/V1/orders?%s' % query_string
                order = req(instance, api_url)
            except Exception as error:
                raise UserError(_("Error while requesting Orders - %s", str(error)))
            for order in order.get('items'):
                queue = self._create_order_queue(instance)
                queue_ids.append(queue.id)
                if len(queue.line_ids) == 50:
                    self._cr.commit()
                    queue = self._create_order_queue(instance)
                    queue_ids.append(queue.id)
                queue_line.create_order_queue_line(instance, order, queue)
        return queue_ids

    @api.model
    def retrieve_dashboard(self, *args, **kwargs):
        dashboard = self.env['queue.line.dashboard']
        return dashboard.get_data(table='magento.order.data.queue.line.ept')

    def process_order_queues(self, is_manual=False):
        start = time.time()
        domain = ['draft', 'cancel', 'failed']
        for queue in self.filtered(lambda q: q.state not in ['completed']):
            cron_name = f"{queue._module}.magento_ir_cron_parent_to_process_order_queue_data"
            process_cron_time = queue.instance_id.get_magento_cron_execution_time(cron_name)
            # To maintain that current queue has started to process.
            queue.write({'is_process_queue': True})
            self._cr.commit()
            log = queue.log_book_id
            if not log:
                log = queue.instance_id.create_log_book(model=queue._name)
                log.write({'res_id': queue.id})
                queue.write({'log_book_id': log.id})
            queue.write({'process_count': queue.process_count + 1})
            if not is_manual and queue.process_count >= 3:
                note = "Attention {} Order Queue is processed 3 times and it failed. " \
                       "\nYou need to process it manually".format(queue.name)
                queue.instance_id.create_schedule_activity(queue=queue, note=note)
                domain.remove('failed')
                queue.write({'is_process_queue': False})
                return True
            lines = queue.line_ids.filtered(lambda l: l.state in domain)
            for line in lines:
                is_processed = line.process_order_queue_line(line, log)
                if is_processed:
                    line.write({'state': 'done', 'processed_at': datetime.now()})
                else:
                    line.write({'state': 'failed', 'processed_at': datetime.now()})
                self._cr.commit()
            message = "Order Queue #{} Processed!!".format(queue.name)
            queue.instance_id.show_popup_notification(message)
            if not log.log_lines:
                log.sudo().unlink()
            # To maintain that current queue process are completed and new queue will be executed.
            queue.write({'is_process_queue': False})
            self._cr.commit()
            if time.time() - start > process_cron_time - 60:
                return True
        return True
