# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import json
from odoo import models, fields

key_list = ['name', 'street', 'street2', 'city', 'zip', 'phone', 'state_id', 'country_id',
            'company_name']


class MagentoResPartnerEpt(models.Model):
    _name = "magento.res.partner.ept"
    _description = "Magento Res Partner"

    partner_id = fields.Many2one(comodel_name="res.partner", string="Customer", ondelete='cascade')
    magento_instance_id = fields.Many2one(comodel_name='magento.instance', string='Instance',
                                          help="This field relocates magento instance")
    magento_website_id = fields.Many2one(comodel_name="magento.website", string="Magento Website",
                                         help="Magento Website")
    magento_customer_id = fields.Char(string="Magento Customer", help="Magento Customer Id")
    address_id = fields.Char(string="Address", help="Address Id")

    def create_magento_customer(self, line, is_order=False):
        if is_order:
            data = line
            instance = line.get('instance_id')
        else:
            data = json.loads(line.data)
            instance = line.instance_id
        customer = False
        if data.get('id'):
            customer = self.__search_customer(id=data.get('id'), instance_id=instance.id)
        if not customer:
            partner = self._create_odoo_partner(data, instance)
            values = self._prepare_magento_customer_values(partner_id=partner.id, instance=instance,
                                                           data=data, customer_id=data.get('id'))
            customer = self.create(values)
        data.update({'parent_id': customer.partner_id.id})
        self._create_customer_addresses(data, instance)
        return data

    def __search_customer(self, **kwargs):
        if kwargs.get('id') in ['Guest Customer', 'Customer Without Id']:
            return self.search([('partner_id.email', '=', kwargs.get('email')),
                                ('magento_instance_id', '=', kwargs.get('instance_id'))], limit=1)
        if kwargs.get('child'):
            return self.search([('magento_customer_id', '=', kwargs.get('customer_id')),
                                ('address_id', '=', kwargs.get('id')),
                                ('magento_instance_id', '=', kwargs.get('instance_id'))], limit=1)
        else:
            return self.search([('magento_customer_id', '=', kwargs.get('id')),
                                ('magento_instance_id', '=', kwargs.get('instance_id'))], limit=1)

    @staticmethod
    def _prepare_magento_customer_values(**kwargs):
        instance = kwargs.get('instance')
        data = kwargs.get('data')
        website = instance.magento_website_ids.filtered(
            lambda w: int(w.magento_website_id) == data.get('website_id'))
        return {
            'partner_id': kwargs.get('partner_id'),
            'magento_instance_id': instance.id,
            'magento_website_id': website and website.id,
            'magento_customer_id': kwargs.get('customer_id'),
            'address_id': kwargs.get('address_id', '')
        }

    def _find_state_country(self, data):
        partner = self.env['res.partner']
        country = partner.get_country(data.get('country_id'))
        state_code = data.get('region', {}).get('region_code')
        zip_code = data.get('postcode')
        state = partner.create_or_update_state_ept(data.get('country_id'), state_code, zip_code,
                                                   country_obj=country)
        return {
            'country_id': country.id,
            'state_id': state.id
        }

    def _create_customer_addresses(self, data, instance):
        parent_id = data.get('parent_id')
        for address in data.get('addresses'):
            address.update({'store_view': data.get('store_view' or False), 'store_id': data.get('store_id' or False)})
            values = self._prepare_partner_values(address, instance, parent_id=parent_id)
            values.update(self._find_state_country(address))
            partner = self.env['res.partner']._find_partner_ept(values, key_list=key_list)
            if not partner:
                company = values.get('company_name', '')
                vat = values.get('vat')
                values.update({'parent_id': parent_id})
                if 'company_name' in list(values.keys()):
                    # We will delete the company_name key form the dictionary,
                    # If we pass that key then odoo will update the value of company_name to False.
                    values.pop('company_name')
                partner = partner.create(values)
                if vat:
                    partner.write({'vat': vat})
                if company:
                    # We will write company_name because we can not pass the company_name and
                    # parent_id together when we write the customer.
                    partner.write({'company_name': company})
            customer = self.__search_customer(child=True, id=address.get('id'),
                                              customer_id=address.get('customer_id'),
                                              instance_id=instance.id)
            if not customer:
                # If customer not found in layer then we will create the customer in layer.
                layer_values = self._prepare_magento_customer_values(instance=instance, data=data,
                                                                     customer_id=address.get(
                                                                         'customer_id'),
                                                                     address_id=address.get('id'),
                                                                     partner_id=partner.id)
                customer.create(layer_values)
            data.update({values.get('type'): partner.id})
        return True

    def _create_odoo_partner(self, data, instance):
        partner = self.env['res.partner']
        partner = partner.search([('email', '=ilike', data.get('email'))])
        if len(partner) > 1:
            # If we found more than 1 customer with same email then we are getting
            # any one customer from it which have not parent_id set.
            partner = partner.search([('email', '=', data.get('email')),
                                      ('parent_id', '=', False)], limit=1)
        if not partner:
            # Add contact=True to identify the address type. Remove the keys from the contact
            # type customer to make the identification of customer easily.
            data.update({'contact': True})
            if 'default_billing' in list(data.keys()):
                del data['default_billing']
            if 'default_shipping' in list(data.keys()):
                del data['default_shipping']
            values = self._prepare_partner_values(data, instance)
            partner = partner.create(values)
        return partner

    @staticmethod
    def __get_type(keys):
        address_type = 'other'
        if 'default_billing' in keys:
            address_type = 'invoice'
        elif 'default_shipping' in keys:
            address_type = 'delivery'
        elif 'contact' in keys:
            address_type = 'contact'
        return address_type

    def _prepare_partner_values(self, data, instance, **kwargs):
        address_type = self.__get_type(list(data.keys()))
        street = self.__merge_street(data.get('street', []))
        magento_store = data.get('store_view') or self.env['magento.storeview'].browse(data.get('store_id'))
        values = {
            'name': f"{data.get('firstname')} {data.get('lastname')}",
            'email': data.get('email'),
            'vat': data.get('vat_id', '') or data.get('taxvat', ''),
            'customer_rank': 1,
            'is_magento_customer': True,
            'street': street.get('street'),
            'street2': street.get('street2'),
            'city': data.get('city', ''),
            'phone': data.get('telephone', ''),
            'zip': data.get('postcode', ''),
            'lang': magento_store.lang_id.code,
            'company_name': data.get('company', False),
            'type': address_type,
            'parent_id': kwargs.get('parent_id', False)
        }
        values = self.env['res.partner'].remove_special_chars_from_partner_vals(values)
        return values

    @staticmethod
    def __merge_street(streets):
        street1 = street2 = ''
        if len(streets):
            street1 = streets[0]
            if len(streets) == 2:
                street2 = streets[1]
            elif len(streets) == 3:
                street2 = f"{streets[1]}, {streets[2]}"
            elif len(streets) == 4:
                street2 = f"{streets[1]}, {streets[2]}, {streets[3]}"
        return {
            'street': street1,
            'street2': street2
        }
