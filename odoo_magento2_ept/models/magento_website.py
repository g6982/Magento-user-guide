# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes Methods for Magento Website.
"""
import json
from datetime import date
from odoo import models, fields, api, _

RES_CURRENCY = "res.currency"


class MagentoWebsite(models.Model):
    """
    Describes Magento Website.
    """
    _name = 'magento.website'
    _description = 'Magento Website'
    _order = 'sort_order ASC, id ASC'

    name = fields.Char(string="Website Name", required=True, readonly=True, help="Website Name")
    sort_order = fields.Integer(string='Website Sort Order', readonly=True,
                                help='Website Sort Order')
    magento_instance_id = fields.Many2one(comodel_name='magento.instance', string='Instance',
                                          ondelete="cascade",
                                          help="This field relocates magento instance")
    magento_website_id = fields.Char(string="Magento Website", help="Magento Website Id")
    import_partners_from_date = fields.Datetime(string='Last partner import date',
                                                help='Date when partner last imported')
    pricelist_ids = fields.Many2many(comodel_name='product.pricelist', string="Pricelists",
                                     help="Product Price is set in selected Pricelist "
                                          "if Catalog Price Scope is Website")
    pricelist_id = fields.Many2one(comodel_name='product.pricelist', string="Pricelist",
                                   help="Product Price is set in selected Pricelist "
                                        "if Catalog Price Scope is Website")
    cost_pricelist_id = fields.Many2one(comodel_name='product.pricelist', string="Cost Pricelist",
                                   help="Product Cost Price is set in selected Pricelist "
                                        "if Catalog Price Scope is Website")
    store_view_ids = fields.One2many(comodel_name="magento.storeview",
                                     inverse_name="magento_website_id",
                                     string='Magento Store Views',
                                     help='This relocates Magento Store Views')
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse',
                                   help='Warehouse to be used to deliver an order from '
                                        'this website.')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', readonly=True,
                                 related='magento_instance_id.company_id',
                                 help="Magento Company")
    currency_id = fields.Many2one(comodel_name="res.currency", related='pricelist_id.currency_id',
                                  readonly=True, help="Currency")
    magento_base_currency = fields.Many2one(comodel_name="res.currency", readonly=True,
                                            help="Magento Website Base Currency")
    active = fields.Boolean(string="Status", default=True)
    color = fields.Integer(string='Color Index')
    magento_order_data = fields.Text(compute="_compute_kanban_magento_order_data")
    website_display_currency = fields.Many2one(comodel_name="res.currency", readonly=True,
                                               help="Display currency of the magento website.")
    m_website_analytic_account_id = fields.Many2one('account.analytic.account',
                                                    string='Magento Analytic Account')
    m_website_analytic_tag_ids = fields.Many2many('account.analytic.tag',
                                                  string='Magento Analytic Tags')
    tax_calculation_method = fields.Selection([
        ('excluding_tax', 'Excluding Tax'), ('including_tax', 'Including Tax')],
        string="Tax Calculation Method into Magento Website", default="excluding_tax",
        help="This indicates whether product prices received from Magento is included tax or not,"
             " when import sale order from Magento")

    def _compute_kanban_magento_order_data(self):
        if not self._context.get('sort'):
            context = dict(self.env.context)
            context.update({'sort': 'week'})
            self.env.context = context
        for record in self:
            # Prepare values for Graph website vise
            values = record.get_graph_data(record)
            data_type, comparison_value = record.get_compare_data(record)
            # Total sales website vise
            total_sales = round(sum([key['y'] for key in values]), 2)
            # Product count website vise query
            exported = 'All'
            product_data = record.get_total_products(record, exported)
            # Customer count website vise query
            customer_data = record.get_customers(record)
            # Order count website vise query
            order_data = record.get_total_orders(record)
            # Order shipped website vise count query
            order_shipped = record.get_shipped_orders(record)
            # refund count query
            refund_data = self.env['magento.instance'].get_refund(record)
            record.magento_order_data = json.dumps({
                "title": "",
                "values": values,
                "area": True,
                "key": "Order: Untaxed amount",
                "color": "#875A7B",
                "total_sales": total_sales,
                "is_sample_data": False,
                "order_data": order_data,
                "customer_data": customer_data,
                "refund_data": refund_data,
                "product_date": product_data,
                "sort_on": self._context.get('sort'),
                "order_shipped": order_shipped,
                "graph_sale_percentage": {'type': data_type, 'value': comparison_value},
                "currency_symbol": record.magento_base_currency.symbol or '',
                # remove currency symbol same as odoo
            })

    @staticmethod
    def prepare_action(view, domain):
        """
        Use: To prepare action dictionary
        :return: action details
        """
        action_dic = {
            'name': view.get('name'),
            'domain': domain,
            'type': view.get('type'),
            'view_id': view.get('view_id')[0] if view.get('view_id') else False,
            'view_mode': view.get('view_mode'),
            'res_model': view.get('res_model'),
            'views': view.get('views'),
            'target': view.get('target'),
        }
        if 'tree' in action_dic['views'][0]:
            action_dic['views'][0] = (action_dic['view_id'], 'list')
        return action_dic

    def get_total_products(self, record, exported, product_type=False):
        """
        Use: To get the list of products exported from Magento website
        Here if exported = True, then only get those record which having sync_product_with_magento= true
        if exported = False, then only get those record which having sync_product_with_magento= false
        if exported = All, then get all those records which having sync_product_with_magento = true and false
        :param product_type: magento product type
        :param record: magento website object
        :param exported: exported is one of the "True" or "False" or "All"
        :return: total number of Magento products ids and action for products
        """
        product_data = {}
        main_sql = """select count(id) as total_count from magento_product_template
        inner join magento_product_template_magento_website_rel on
        magento_product_template_magento_website_rel.magento_product_template_id = magento_product_template.id  
        where magento_product_template_magento_website_rel.magento_website_id = %s and
        magento_product_template.magento_instance_id = %s""" % (
            record.id, record.magento_instance_id.id)
        product_domain = []
        if exported != 'All' and exported:
            main_sql = main_sql + " and magento_product_template.sync_product_with_magento = True"
            product_domain.append(('sync_product_with_magento', '=', True))
        elif not exported:
            main_sql = main_sql + " and magento_product_template.sync_product_with_magento = False"
            product_domain.append(('sync_product_with_magento', '=', False))
        elif exported == 'All':
            product_domain.append(('sync_product_with_magento', 'in', (False, True)))

        if product_type:
            product_domain.append(('product_type', '=', product_type))
        self._cr.execute(main_sql)
        result = self._cr.dictfetchall()
        total_count = 0
        if result:
            total_count = result[0].get('total_count')
        view = self.env.ref('odoo_magento2_ept.action_magento_product_exported_ept').sudo().read()[
            0]
        product_domain.append(('magento_instance_id', '=', record.magento_instance_id.id))
        product_domain.append(('magento_website_ids', '=', record.name))
        action = record.prepare_action(view, product_domain)
        product_data.update({'product_count': total_count, 'product_action': action})
        return product_data

    def get_customers(self, record):
        """
        Use: To get the list of customers with Magento instance for current Magento instance
        :return: total number of customer ids and action for customers
        """
        customer_data = {}
        main_sql = """select DISTINCT(rp.id) as partner_id from res_partner as rp
                        inner join magento_res_partner_ept mp on mp.partner_id = rp.id
                        where mp.magento_website_id = %s and
                        mp.magento_instance_id = %s""" % (record.id, record.magento_instance_id.id)
        view = self.env.ref('base.action_partner_form').sudo().read()[0]
        self._cr.execute(main_sql)
        result = self._cr.dictfetchall()
        magento_customer_ids = []
        if result:
            for data in result:
                magento_customer_ids.append(data.get('partner_id'))
        action = record.prepare_action(view, [('id', 'in', magento_customer_ids)])
        customer_data.update(
            {'customer_count': len(magento_customer_ids), 'customer_action': action})
        return customer_data

    def get_total_orders(self, record, state=False):
        """
        Use: To get the list of Magento sale orders month wise or year wise
        :return: total number of Magento sale orders ids and action for sale orders of current instance
        """
        if not state:
            state = ('sale', 'done')

        def orders_of_current_week(record):
            self._cr.execute("""select id from sale_order where date(date_order)
                                >= (select date_trunc('week', date(current_date)))
                                and magento_instance_id= %s and state in %s 
                                and magento_website_id = %s 
                                order by date(date_order)
                        """ % (record.magento_instance_id.id, state, record.id))
            return self._cr.dictfetchall()

        def orders_of_current_month(record):
            self._cr.execute("""select id from sale_order where date(date_order) >=
                                (select date_trunc('month', date(current_date)))
                                and magento_instance_id= %s and state in %s 
                                and magento_website_id = %s
                                order by date(date_order)
                        """ % (record.magento_instance_id.id, state, record.id))
            return self._cr.dictfetchall()

        def orders_of_current_year(record):
            self._cr.execute("""select id from sale_order where date(date_order) >=
                                (select date_trunc('year', date(current_date))) 
                                and magento_instance_id= %s and state in %s  
                                and magento_website_id = %s
                                order by date(date_order)
                             """ % (record.magento_instance_id.id, state, record.id))
            return self._cr.dictfetchall()

        def orders_of_all_time(record):
            self._cr.execute(
                """select id from sale_order where magento_instance_id = %s
                and state in %s
                and magento_website_id = %s""" % (record.magento_instance_id.id, state, record.id))
            return self._cr.dictfetchall()

        magento_order_data = {}
        magento_order_ids = []
        if self._context.get('sort') == "week":
            results = orders_of_current_week(record)
        elif self._context.get('sort') == "month":
            results = orders_of_current_month(record)
        elif self._context.get('sort') == "year":
            results = orders_of_current_year(record)
        else:
            results = orders_of_all_time(record)
        if results:
            for data in results:
                magento_order_ids.append(data.get('id'))
        view = self.env.ref('odoo_magento2_ept.magento_action_sales_order_ept').sudo().read()[0]
        order_action = record.prepare_action(view, [('id', 'in', magento_order_ids)])
        magento_order_data.update(
            {'order_count': len(magento_order_ids), 'order_action': order_action})
        return magento_order_data

    def get_shipped_orders(self, record):
        """
        Use: To get the list of Magento shipped orders month wise or year wise
        :return: total number of Magento shipped orders ids and action for shipped orders of current instance
        """
        shipped_query = """
            SELECT distinct(so.id) 
            FROM stock_picking AS sp
            JOIN sale_order AS so
                ON sp.sale_id = so.id
            JOIN stock_location AS sl 
                ON sl.id = sp.location_dest_id 
            WHERE 
                sp.is_magento_picking = True AND 
                sp.state = 'done' AND
                so.magento_instance_id = {} AND
                so.magento_website_id = {} AND
                sl.usage='customer'
        """.format(record.magento_instance_id.id, record.id)

        def website_vise_shipped_order_of_current_week(shipped_query):
            qry = shipped_query + " and date(so.date_order) >= (select date_trunc('week', date(current_date)))"
            self._cr.execute(qry)
            return self._cr.dictfetchall()

        def website_vise_shipped_order_of_current_month(shipped_query):
            qry = shipped_query + " and date(so.date_order) >= (select date_trunc('month', date(current_date)))"
            self._cr.execute(qry)
            return self._cr.dictfetchall()

        def website_vise_shipped_order_of_current_year(shipped_query):
            qry = shipped_query + " and date(so.date_order) >= (select date_trunc('year', date(current_date)))"
            self._cr.execute(qry)
            return self._cr.dictfetchall()

        def website_vise_shipped_order_of_all_time(shipped_query):
            self._cr.execute(shipped_query)
            return self._cr.dictfetchall()

        order_data = {}
        order_ids = []
        if self._context.get('sort') == "week":
            result = website_vise_shipped_order_of_current_week(shipped_query)
        elif self._context.get('sort') == "month":
            result = website_vise_shipped_order_of_current_month(shipped_query)
        elif self._context.get('sort') == "year":
            result = website_vise_shipped_order_of_current_year(shipped_query)
        else:
            result = website_vise_shipped_order_of_all_time(shipped_query)
        if result:
            for data in result:
                order_ids.append(data.get('id'))
        view = self.env.ref('odoo_magento2_ept.magento_action_sales_order_ept').sudo().read()[0]
        shipped_order_action = record.prepare_action(view, [('id', 'in', order_ids)])
        order_data.update({'order_count': len(order_ids), 'order_action': shipped_order_action})
        return order_data

    def magento_product_exported_ept(self):
        """
        get exported as true product action
        :return:
        """
        exported = True
        exported_product_data = self.get_total_products(self, exported)
        return exported_product_data.get('product_action')

    def action_magento_simple_product_type(self):
        """
        get magento simple product type
        :return:
        """
        product_type = "simple"
        exported = "All"
        simple_product_data = self.get_total_products(self, exported, product_type)
        return simple_product_data.get('product_action')

    def action_magento_configurable_product_type(self):
        """
        get magento configurable product type
        :return:
        """
        product_type = "configurable"
        exported = "All"
        configurable_product_data = self.get_total_products(self, exported, product_type)
        return configurable_product_data.get('product_action')

    def magento_action_sales_quotations_ept(self):
        """
        get quotations action
        :return:
        """
        state = ('draft', 'sent')
        order_quotation_data = self.get_total_orders(self, state)
        return order_quotation_data.get('order_action')

    def magento_action_sales_order_ept(self):
        """
        get sales order action
        :return:
        """
        state = ('sale', 'done')
        sale_order_data = self.get_total_orders(self, state)
        return sale_order_data.get('order_action')

    def get_magento_invoice_records(self, state):
        """
        To get instance wise magento invoice
        :param state: state of the invoice
        :return: invoice_data dict with total count and action
        """
        magento_invoice_data = {}
        magento_invoice_ids = []
        magento_invoice_query = """select account_move.id
        from sale_order_line_invoice_rel
        inner join sale_order_line on sale_order_line.id=sale_order_line_invoice_rel.order_line_id 
        inner join sale_order on sale_order.id=sale_order_line.order_id
        inner join account_move_line on account_move_line.id=sale_order_line_invoice_rel.invoice_line_id 
        inner join account_move on account_move.id=account_move_line.move_id
        where sale_order.magento_website_id=%s
        and sale_order.magento_instance_id=%s
        and account_move.state in ('%s')
        and account_move.move_type in ('out_invoice','out_refund')""" % \
                                (self.id, self.magento_instance_id.id, state)
        self._cr.execute(magento_invoice_query)
        result = self._cr.dictfetchall()
        view = self.env.ref('odoo_magento2_ept.action_magento_invoice_tree1_ept').sudo().read()[0]
        if result:
            for data in result:
                magento_invoice_ids.append(data.get('id'))
        action = self.prepare_action(view, [('id', 'in', magento_invoice_ids)])
        magento_invoice_data.update(
            {'order_count': len(magento_invoice_ids), 'order_action': action})
        return magento_invoice_data

    def get_magento_picking_records(self, state):
        """
        To get instance wise magento picking
        :param state: state of the picking
        :return: picking_data dict with total count and action
        """
        magento_picking_data = {}
        magento_picking_ids = []
        magento_picking_query = """SELECT SP.id FROM stock_picking as SP
        inner join sale_order as SO on SP.sale_id = SO.id
        inner join stock_location as SL on SL.id = SP.location_dest_id 
        WHERE SP.magento_instance_id = %s
        and SO.magento_website_id = %s
        and SL.usage = 'customer'
        and SP.state in ('%s')
        """ % (self.magento_instance_id.id, self.id, state)
        self._cr.execute(magento_picking_query)
        result = self._cr.dictfetchall()
        view = \
            self.env.ref('odoo_magento2_ept.action_magento_stock_picking_tree_ept').sudo().read()[0]
        if result:
            for data in result:
                magento_picking_ids.append(data.get('id'))
        action = self.prepare_action(view, [('id', 'in', magento_picking_ids)])
        magento_picking_data.update(
            {'order_count': len(magento_picking_ids), 'order_action': action})
        return magento_picking_data

    def magento_invoice_invoices_open(self):
        """
        get draft state invoice action
        :return:
        """
        state = 'draft'
        draft_invoice_data = self.get_magento_invoice_records(state)
        return draft_invoice_data.get('order_action')

    def magento_invoice_invoices_paid(self):
        """
        get posted state invoice action
        :return:
        """
        state = 'posted'
        posted_invoice_data = self.get_magento_invoice_records(state)
        return posted_invoice_data.get('order_action')

    def magento_waiting_stock_picking_ept(self):
        """
        get confirmed state picking action
        :return:
        """
        state = 'confirmed'
        confirmed_picking_data = self.get_magento_picking_records(state)
        return confirmed_picking_data.get('order_action')

    def magento_partially_available_stock_picking_ept(self):
        """
        get partially_available state picking action
        :return:
        """
        state = 'partially_available'
        partially_available_picking_data = self.get_magento_picking_records(state)
        return partially_available_picking_data.get('order_action')

    def magento_ready_stock_picking_ept(self):
        """
        get assigned state picking action
        :return:
        """
        state = 'assigned'
        assigned_picking_data = self.get_magento_picking_records(state)
        return assigned_picking_data.get('order_action')

    def magento_transferred_stock_picking_ept(self):
        """
        get done state picking action
        :return:
        """
        state = 'done'
        done_picking_data = self.get_magento_picking_records(state)
        return done_picking_data.get('order_action')

    @api.model
    def perform_operation(self, record_id):
        """
        Use: To prepare Magento operation action
        :return: Magento operation action details
        """
        view = self.env.ref('odoo_magento2_ept.'
                            'action_wizard_magento_instance_import_export_operations').sudo().read()[
            0]
        action = self.prepare_action(view, [])
        website = self.browse(record_id)
        action.update(
            {'context': {'default_magento_instance_ids': website.magento_instance_id.ids}})
        return action

    @api.model
    def open_logs(self, record_id):
        """
        Use: To prepare Magento logs action
        :return: Magento logs action details
        """
        website = self.browse(record_id)
        view = self.env.ref('odoo_magento2_ept.action_common_log_book_ept_magento').sudo().read()[0]
        return self.prepare_action(view,
                                   [('magento_instance_id', '=', website.magento_instance_id.id)])

    @api.model
    def open_report(self, record_id):
        """
        Use: To prepare Magento report action
        :return: Magento report action details
        """
        view = self.env.ref('odoo_magento2_ept.magento_sale_report_action_dashboard').sudo().read()[0]
        website = self.browse(record_id)
        action = self.prepare_action(view,
                                     [('magento_instance_id', '=', website.magento_instance_id.id),
                                      ('magento_website_id', '=', record_id)])

        action.update({'context': {'search_default_magento_websites': record_id, 'search_default_Sales': 1,
                                   'search_default_filter_date': 1, '': record_id}})
        return action

    def get_graph_data(self, record):
        """
        Use: To get the details of Magento sale orders and total amount month wise or year wise to prepare the graph
        :return: Magento sale order date or month and sum of sale orders amount of current instance
        """

        def get_current_week_date(record):
            self._cr.execute("""SELECT to_char(date(d.day),'DAY'), t.amount_untaxed as sum
                                FROM  (
                                   SELECT day
                                   FROM generate_series(date(date_trunc('week', (current_date)))
                                    , date(date_trunc('week', (current_date)) + interval '6 days')
                                    , interval  '1 day') day
                                   ) d
                                LEFT   JOIN 
                                (SELECT date(date_order)::date AS day, sum(amount_untaxed) as amount_untaxed
                                   FROM   sale_order
                                   WHERE  date(date_order) >= (select date_trunc('week', date(current_date)))
                                   AND    date(date_order) <= (select date_trunc('week', date(current_date)) 
                                   + interval '6 days')
                                   AND magento_instance_id=%s and state in ('sale','done') 
                                    AND magento_website_id = %s 
                                   GROUP  BY 1
                                   ) t USING (day)
                                ORDER  BY day""", (record.magento_instance_id.id, record.id))
            return self._cr.dictfetchall()

        def graph_of_current_month(record):
            self._cr.execute("""select EXTRACT(DAY from date(date_day)) :: integer,sum(amount_untaxed) from (
                        SELECT 
                          day::date as date_day,
                          0 as amount_untaxed
                        FROM generate_series(date(date_trunc('month', (current_date)))
                            , date(date_trunc('month', (current_date)) + interval '1 MONTH - 1 day')
                            , interval  '1 day') day
                        union all
                        SELECT date(date_order)::date AS date_day,
                        sum(amount_untaxed) as amount_untaxed
                          FROM   sale_order
                        WHERE  date(date_order) >= (select date_trunc('month', date(current_date)))
                        AND date(date_order)::date <= (select date_trunc('month', date(current_date)) 
                        + '1 MONTH - 1 day')
                        and magento_instance_id = %s and state in ('sale','done') 
                        and magento_website_id = %s 
                        group by 1
                        )foo 
                        GROUP  BY 1
                        ORDER  BY 1""", (record.magento_instance_id.id, record.id))
            return self._cr.dictfetchall()

        def graph_of_current_year(record):
            self._cr.execute("""select TRIM(TO_CHAR(DATE_TRUNC('month',month),'MONTH')),sum(amount_untaxed) from
                                (SELECT DATE_TRUNC('month',date(day)) as month,
                                  0 as amount_untaxed
                                FROM generate_series(date(date_trunc('year', (current_date)))
                                , date(date_trunc('year', (current_date)) + interval '1 YEAR - 1 day')
                                , interval  '1 MONTH') day
                                union all
                                SELECT DATE_TRUNC('month',date(date_order)) as month,
                                sum(amount_untaxed) as amount_untaxed
                                  FROM   sale_order
                                WHERE  date(date_order) >= (select date_trunc('year', date(current_date))) AND 
                                date(date_order)::date <= (select date_trunc('year', date(current_date)) 
                                + '1 YEAR - 1 day')
                                and magento_instance_id = %s and state in ('sale','done') 
                                and magento_website_id = %s 
                                group by DATE_TRUNC('month',date(date_order))
                                order by month
                                )foo 
                                GROUP  BY foo.month
                                order by foo.month""", (record.magento_instance_id.id, record.id))
            return self._cr.dictfetchall()

        def graph_of_all_time(record):
            self._cr.execute("""select TRIM(TO_CHAR(DATE_TRUNC('month',date_order),'YYYY-MM')),sum(amount_untaxed)
                                from sale_order where magento_instance_id = %s and state in ('sale','done') 
                                and magento_website_id = %s 
                                group by DATE_TRUNC('month',date_order) 
                                order by DATE_TRUNC('month',date_order)""",
                             (record.magento_instance_id.id, record.id))
            return self._cr.dictfetchall()

        # Prepare values for Graph
        values = []
        if self._context.get('sort') == 'week':
            website_vise_result = get_current_week_date(record)
        elif self._context.get('sort') == "month":
            website_vise_result = graph_of_current_month(record)
        elif self._context.get('sort') == "year":
            website_vise_result = graph_of_current_year(record)
        else:
            website_vise_result = graph_of_all_time(record)
        if website_vise_result:
            for data in website_vise_result:
                values.append({"x": ("{}".format(data.get(list(data.keys())[0]))),
                               "y": data.get('sum') or 0.0})
        return values

    def get_compare_data(self, record):
        """
        :param record: Magento instance
        :return: Comparison ratio of orders (weekly,monthly and yearly based on selection)
        """
        data_type = False
        total_percentage = 0.0

        if self._context.get('sort') == 'week':
            website_current_total, website_previous_total = self.get_compared_week_data(record)
        elif self._context.get('sort') == "month":
            website_current_total, website_previous_total = self.get_compared_month_data(record)
        elif self._context.get('sort') == "year":
            website_current_total, website_previous_total = self.get_compared_year_data(record)
        else:
            website_current_total, website_previous_total = 0.0, 0.0
        if website_current_total > 0.0:
            if website_current_total >= website_previous_total:
                data_type = 'positive'
                total_percentage = (
                                           website_current_total - website_previous_total) * 100 / website_current_total
            if website_previous_total > website_current_total:
                data_type = 'negative'
                total_percentage = (
                                           website_previous_total - website_current_total) * 100 / website_current_total
        return data_type, round(total_percentage, 2)

    def get_compared_week_data(self, record):
        website_current_total = 0.0
        website_previous_total = 0.0
        day_of_week = date.weekday(date.today())
        self._cr.execute("""select sum(amount_untaxed) as current_week from sale_order
                            where date(date_order) >= (select date_trunc('week', date(current_date))) and
                            magento_instance_id=%s and magento_website_id = %s and state in ('sale','done')""",
                         (record.magento_instance_id.id, record.id))
        current_week_data = self._cr.dictfetchone()
        if current_week_data and current_week_data.get('current_week'):
            website_current_total = current_week_data.get('current_week')
        # Previous week data
        self._cr.execute("""select sum(amount_untaxed) as previous_week from sale_order
                        where date(date_order) between (select date_trunc('week', current_date) - interval '7 day') 
                        and (select date_trunc('week', (select date_trunc('week', current_date) - interval '7
                        day')) + interval '%s day')
                        and magento_instance_id=%s and magento_website_id = %s and state in ('sale','done')
                        """, (day_of_week, record.magento_instance_id.id, record.id))
        previous_week_data = self._cr.dictfetchone()
        if previous_week_data and previous_week_data.get('previous_week'):
            website_previous_total = previous_week_data.get('previous_week')
        return website_current_total, website_previous_total

    def get_compared_month_data(self, record):
        website_current_total = 0.0
        website_previous_total = 0.0
        day_of_month = date.today().day - 1
        self._cr.execute("""select sum(amount_untaxed) as current_month from sale_order
                            where date(date_order) >= (select date_trunc('month', date(current_date)))
                            and magento_instance_id=%s and magento_website_id = %s and state in ('sale','done')""",
                         (record.magento_instance_id.id, record.id))
        current_data = self._cr.dictfetchone()
        if current_data and current_data.get('current_month'):
            website_current_total = current_data.get('current_month')
        # Previous week data
        self._cr.execute("""select sum(amount_untaxed) as previous_month from sale_order where date(date_order)
                        between (select date_trunc('month', current_date) - interval '1 month') and
                        (select date_trunc('month', (select date_trunc('month', current_date) - interval
                        '1 month')) + interval '%s days')
                        and magento_instance_id=%s and magento_website_id = %s and state in ('sale','done')
                        """, (day_of_month, record.magento_instance_id.id, record.id))
        previous_data = self._cr.dictfetchone()
        if previous_data and previous_data.get('previous_month'):
            website_previous_total = previous_data.get('previous_month')
        return website_current_total, website_previous_total

    def get_compared_year_data(self, record):
        website_current_total = 0.0
        website_previous_total = 0.0
        year_begin = date.today().replace(month=1, day=1)
        year_end = date.today()
        delta = (year_end - year_begin).days - 1
        self._cr.execute("""select sum(amount_untaxed) as current_year from sale_order
                            where date(date_order) >= (select date_trunc('year', date(current_date)))
                            and magento_instance_id=%s and magento_website_id = %s and state in ('sale','done')""",
                         (record.magento_instance_id.id, record.id))
        current_data = self._cr.dictfetchone()
        if current_data and current_data.get('current_year'):
            website_current_total = current_data.get('current_year')
        # Previous week data
        self._cr.execute("""select sum(amount_untaxed) as previous_year from sale_order where date(date_order)
                        between (select date_trunc('year', date(current_date) - interval '1 year')) and 
                        (select date_trunc('year', date(current_date) - interval '1 year') + interval '%s days') 
                        and magento_instance_id=%s and magento_website_id = %s and state in ('sale','done')
                        """, (delta, record.magento_instance_id.id, record.id))
        previous_data = self._cr.dictfetchone()
        if previous_data and previous_data.get('previous_year'):
            website_previous_total = previous_data.get('previous_year')
        return website_current_total, website_previous_total

    def open_store_views(self):
        """
        This method used to view all store views for website.
        """
        form_view_id = self.env.ref('odoo_magento2_ept.view_magento_storeview_form').id
        tree_view = self.env.ref('odoo_magento2_ept.view_magento_storeview_tree').id
        action = {
            'name': 'Magento Store Views',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'magento.storeview',
            'views': [(tree_view, 'tree'), (form_view_id, 'form')],
            'view_id': tree_view,
            'target': 'current',
            'domain': [('id', 'in', self.store_view_ids.ids)]
        }
        return action

    def show_instance(self):
        """
        Use: To prepare Magento Instance action
        :return: Magento Instance action details
        """
        view_ref = self.env.ref('odoo_magento2_ept.view_magento_instance_form').ids
        view_id = view_ref if view_ref else False
        return {
            'name': _('Magento Instance'),
            'res_model': 'magento.instance',
            'type': 'ir.actions.act_window',
            'views': [(view_id, 'form')],
            'view_mode': 'form',
            'view_id': view_id,
            'res_id': self.magento_instance_id.id,
            'target': 'current'
        }

    def show_storeview(self):
        """
        Use: To prepare Magento Store View action
        :return: Magento Store View action details
        """
        view = self.env.ref('odoo_magento2_ept.action_magento_storeview').sudo().read()[0]
        action = self.prepare_action(view, [('id', 'in', self.store_view_ids.ids)])
        action.update({'context': {'default_id': self.magento_instance_id.id}})
        return action

    def get_draft_refund(self):
        context = self.env.context
        state = f"('{context.get('state')}')"
        result = self.env['magento.instance'].get_refund(self.magento_instance_id, self.id, state)
        return result.get('refund_action')

    def get_posted_refund(self):
        context = self.env.context
        state = f"('{context.get('state')}')"
        result = self.env['magento.instance'].get_refund(self.magento_instance_id, self.id, state)
        return result.get('refund_action')

    def get_cancelled_refund(self):
        context = self.env.context
        state = f"('{context.get('state')}')"
        result = self.env['magento.instance'].get_refund(self.magento_instance_id, self.id, state)
        return result.get('refund_action')
