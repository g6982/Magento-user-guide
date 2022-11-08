# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes Magento Inventory Locations
"""
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MagentoInventoryLocations(models.Model):
    """
    Describes Magento Inventory Locations
    """
    _name = 'magento.inventory.locations'
    _description = "Magento Inventory Locations"
    _order = 'id ASC'

    name = fields.Char(string="Magento Location Name", required=True, readonly=True,
                       help="Magento Inventory Location Name")
    magento_location_code = fields.Char(string="Magento MSI Code", readonly=True,
                                        help="Store view Code")
    magento_instance_id = fields.Many2one(comodel_name='magento.instance', string='Instance',
                                          ondelete='cascade',
                                          help="This field relocates magento instance")
    export_stock_warehouse_ids = fields.Many2many(
        comodel_name='stock.warehouse',
        string="Warehouses",
        help='If you have product stock in various Warehouses that you need to export in the '
             'Magento, \n then configure current odoo Warehouses here for the current stock '
             'location. \n It will compute the stock quantities from those Warehouses \n'
             'and export them to the current source location in the Magento.')
    import_stock_warehouse = fields.Many2one(comodel_name='stock.warehouse',
                                             string="Import Product Stock Warehouse",
                                             help="Warehouse for import stock from Magento to Odoo")
    active = fields.Boolean(string="Status", default=True)
    ship_from_location = fields.Many2one(comodel_name='stock.location',
                                         string='Export Shipment Location',
                                         domain=lambda self: self._domain_stock_locations(),
                                         help="Location for export shipment from Odoo to Magento")

    def _domain_stock_locations(self):
        stock_locations = self.env['stock.warehouse'].search([]).lot_stock_id
        return [('id', 'in', stock_locations.ids)]

    @api.constrains('export_stock_warehouse_ids')
    def _check_locations_warehouse_ids(self):
        """ Do not save or update location if warehouse already set in different location with same instance.
        :return:
        @param : self
        """
        location_instance = self.magento_instance_id
        location_warehouse = self.export_stock_warehouse_ids
        locations = self.search(
            [('magento_instance_id', '=', location_instance.id), ('id', '!=', self.id)])
        for location in locations:
            if any([location in location_warehouse.ids for location in
                    location.export_stock_warehouse_ids.ids]):
                raise ValidationError(_("Can't set this warehouse in "
                                        "different locations with same instance."))

    @api.constrains('ship_from_location')
    def _check_ship_from_location(self):
        """
        Do not update or save location if it is used into other inventor locations with same instance
        :return:
        """
        inv_locs = self.search([
            ('ship_from_location', '=', self.ship_from_location.id),
            ('magento_instance_id', '=', self.magento_instance_id.id)])
        for inv_loc in inv_locs:
            if inv_locs and inv_loc.id != self.id:
                raise ValidationError(
                    _("It is not possible to set this location multiple times in the same "
                      "instance because it is used with another inventory location"))
