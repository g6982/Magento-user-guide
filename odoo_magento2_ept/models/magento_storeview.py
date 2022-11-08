# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes Magento Store View
"""
from odoo import models, fields


class MagentoStoreview(models.Model):
    """
    Describes Magento Store View
    """
    _name = 'magento.storeview'
    _description = "Magento Storeview"
    _order = 'sort_order ASC, id ASC'

    name = fields.Char(string="Store view Name", required=True, readonly=True,
                       help="Store view Name")
    sort_order = fields.Integer(string='Website Sort Order', readonly=True,
                                help='Website Sort Order')
    magento_website_id = fields.Many2one(comodel_name='magento.website', string="Website",
                                         help="This field relocates Magento Website", )
    lang_id = fields.Many2one(comodel_name='res.lang', string='Language', help="Language Name")
    team_id = fields.Many2one(comodel_name='crm.team', string='Sales Team', help="Sales Team")
    magento_storeview_id = fields.Char(string="Magento Store View", help="Magento Store View")
    magento_storeview_code = fields.Char(string="Magento Store Code", help="Magento Store Code")
    magento_instance_id = fields.Many2one(comodel_name='magento.instance',
                                          related='magento_website_id.magento_instance_id',
                                          ondelete="cascade", string='Instance', store=True,
                                          readonly=True, required=False,
                                          help="This field relocates magento instance")
    import_orders_from_date = fields.Datetime(string='Import sale orders from date',
                                              help='Do not consider non-imported sale orders before'
                                                   ' this date. Leave empty to import all sale '
                                                   'orders')
    base_media_url = fields.Char(string='Base Media URL', help="URL for Image store at Magento.")
    active = fields.Boolean(string="Status", default=True)
    sale_prefix = fields.Char(string="Sale Order Prefix",
                              help="A prefix put before the name of imported sales orders.\n"
                                   "For example, if the prefix is 'mag-', the sales "
                                   "order 100000692 in Magento, will be named 'mag-100000692' "
                                   "in ERP.")
    is_use_odoo_order_sequence = fields.Boolean(string="Is Use Odoo Order Sequences?",
                                                default=False,
                                                help="If checked, Odoo Order Sequence is used")
