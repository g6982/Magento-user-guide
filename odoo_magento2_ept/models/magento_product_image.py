# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods to create magento product images
"""
import base64
import requests
from odoo import models, api, fields


class MagentoProductImage(models.Model):
    """
    Describes methods to create magento product images
    """
    _name = 'magento.product.image'
    _description = "Magento product image"

    def get_image(self):
        """
        Get image from image url
        :return: Binary Image or False
        """
        for image in self:
            if image.link:
                if image.url:
                    response = requests.get(image.url)
                    if response.ok and response.content:
                        img = base64.b64encode(response.content)
                    else:
                        img = False
                else:
                    return False
            else:
                img = image.file_db_store
            return img

    def _compute_get_image(self):
        """
        Get image from image response
        :return: Binary Image or False
        """
        for each in self:
            if each.url:
                response = requests.get(each.url)
                if response.ok and response.content:
                    img = base64.b64encode(response.content)
                else:
                    img = False
            each.file = img

    odoo_image_id = fields.Many2one(comodel_name="common.product.image.ept",
                                    ondelete="cascade", string="Odoo Images", help="Odoo Images")
    magento_instance_id = fields.Many2one(comodel_name='magento.instance', string='Instance',
                                          ondelete="cascade",
                                          help="This field relocates magento instance")
    magento_image_id = fields.Char(string="Magento Product Image Id",
                                   help="Magento Product Image ID")
    magento_product_id = fields.Many2one(comodel_name='magento.product.product',
                                         string="Magento Product", ondelete="cascade",
                                         help="Magento Product")
    magento_tmpl_id = fields.Many2one(comodel_name='magento.product.template',
                                      string="Magento Template", ondelete="cascade",
                                      help="Magento Product Template")
    name = fields.Text(string='File Name', help="File name")
    image = fields.Image(related="odoo_image_id.image", string="Product Image",
                         help="Magento Product Image")
    url = fields.Char(string='File Location', help="Image URL")
    sequence = fields.Integer(string='Image Sequence',
                              help="The sequence number will use this to order the product images")
    exported_in_magento = fields.Boolean(string="Image Exported In Magento?", default=False,
                                         help="Image Exported In Magento?")

    @api.model
    def default_get(self, fields):
        """
        we have inherited default_get method for setting
        default value of template_id and product_id
        in context for select variant wise images.
        """
        fields += ["magento_tmpl_id", "magento_product_id"]
        return super(MagentoProductImage, self).default_get(fields)

    # @api.model
    # def create(self, vals):
    #     """
    #     Inherited for adding image from URL.
    #     """
    # if not vals.get("image", False) and vals.get("url", ""):
    #     image = self.get_image()
    #     vals.update({"image": image})
    # rec = super(MagentoProductImage, self).create(vals)
    # base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    # rec_id = str(rec.id)
    # url = base_url + '/lf/i/%s' % (base64.urlsafe_b64encode(rec_id.encode("utf-8")).decode(
    #     "utf-8"))
    # rec.write({'url': url, 'image_binary': vals.get('image')})
    # return super(MagentoProductImage, self).create(vals)
