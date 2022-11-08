# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods to store images from Magento.
"""
from odoo import models, fields, api


MAGENTO_PRODUCT_IMAGE = "magento.product.image"


class CommonProductImageEpt(models.Model):
    """
    store image from Magento
    Upload product images to Magento
    """
    _inherit = 'common.product.image.ept'

    magento_image_ids = fields.One2many(comodel_name="magento.product.image",
                                        inverse_name="odoo_image_id",
                                        string='Magento Product Images',
                                        help="Magento Product Images")

    @api.model
    def create(self, vals):
        """
        Inherited for adding images in Magento products.
        """
        result = super(CommonProductImageEpt, self).create(vals)
        if self.user_has_groups('odoo_magento2_ept.group_magento_user_ept'):
            magento_product_template_obj = self.env["magento.product.template"]
            magento_product_image_obj = self.env[MAGENTO_PRODUCT_IMAGE]
            magento_product_image_vals = {"odoo_image_id": result.id}

            if vals.get("product_id", False):
                self.create_magento_variant_product_images(result,
                magento_product_image_vals, vals)
            elif vals.get("template_id", False):
                magento_templates = magento_product_template_obj.search_read(
                    [("odoo_product_template_id", "=", vals.get("template_id"))], ["id"])
                for magento_template in magento_templates:
                    existing_gallery_images = magento_product_template_obj.browse(
                        magento_template["id"]).magento_product_image_ids.filtered(lambda x:
                        not x.magento_product_id)
                    sequence = 1
                    for existing_gallery_image in existing_gallery_images:
                        existing_gallery_image.write({"sequence": sequence})
                        sequence = sequence + 1
                    magento_product_image_vals.update({
                        "magento_tmpl_id": magento_template["id"], "sequence": "0",
                        "image": result.image
                    })
                    magento_product_image_obj.create(magento_product_image_vals)

        return result

    def create_magento_variant_product_images(self, result, magento_product_image_vals, vals):
        """
        Create product image for Magento product variants
        :param result: common product image object
        :param magento_product_image_vals: dictionary for v product image
        :param vals: response received from Magento
        """
        magento_product_image_obj = self.env[MAGENTO_PRODUCT_IMAGE]
        magento_product_product_obj = self.env["magento.product.product"]
        magento_variants = magento_product_product_obj.search_read([
            ("odoo_product_id", "=", vals.get("product_id"))], ["id", "magento_tmpl_id"])
        sequence = 1
        for magento_variant in magento_variants:
            variant_gallery_images = magento_product_product_obj.browse(magento_variant["id"]).magento_product_image_ids
            for variant_gallery_image in variant_gallery_images:
                variant_gallery_image.write({"sequence": sequence})
                sequence = sequence + 1
            magento_product_image_vals.update({
                "magento_product_id": magento_variant["id"],
                "magento_tmpl_id": magento_variant["magento_tmpl_id"][0],
                "image": result.image,
                "sequence": "0"})
            magento_product_image_obj.create(magento_product_image_vals)

    def write(self, vals):
        """
        Inherited for adding images in Magento products.
        """
        result = super(CommonProductImageEpt, self).write(vals)
        if self.user_has_groups('odoo_magento2_ept.group_magento_user_ept'):
            magento_product_images = self.env[MAGENTO_PRODUCT_IMAGE]
            for record in self:
                magento_product_images += magento_product_images.search([("odoo_image_id", "=", record.id)])
            if magento_product_images:
                if not vals.get("product_id", ""):
                    magento_product_images.write({"magento_product_id": False})
                elif vals.get("product_id", ""):
                    self.link_image_to_magento_variant(magento_product_images, vals)
        return result

    def link_image_to_magento_variant(self, magento_product_images, vals):
        magento_product_product_obj = self.env["magento.product.product"]
        for magento_product_image in magento_product_images:
            magento_variant = magento_product_product_obj.search_read(
                [("product_id", "=", vals.get("product_id")),
                 ("magento_template_id", "=", magento_product_image.magento_tmpl_id.id)], ["id"])
            if magento_variant:
                magento_product_image.write({"magento_product_id": magento_variant[0]["id"]})
