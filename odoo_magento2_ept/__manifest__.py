{
    # App information
    'name': "Odoo Magento 2 Connector",
    'version': '15.0.2.6.2',
    'category': 'Sales',
    'license': 'OPL-1',
    'summary': 'Odoo Magento 2 Connector helps you integrate your Magento 2.x website with Odoo and automates various operations between Odoo and Magento.Apart from Odoo Magento Connector, we do have other ecommerce solutions or applications such as Woocommerce connector , Shopify connector , and also we have solutions for Marketplace Integration such as Odoo Amazon connector , Odoo eBay Connector , Odoo Walmart Connector , Odoo Bol.com Connector.Aside from ecommerce integration and ecommerce marketplace integration, we also provide solutions for various operations, such as shipping , logistics , shipping labels , and shipping carrier management with our shipping integration , known as the Shipstation connector.For the customers who are into Dropship business, we do provide EDI Integration that can help them manage their Dropshipping business with our Dropshipping integration or Dropshipper integration It is listed as Dropshipping EDI integration and Dropshipper EDI integration.Emipro applications can be searched with different keywords like Amazon integration , Shopify integration , Woocommerce integration, Magento integration , Amazon vendor center module , Amazon seller center module , Inter company transfer , Ebay integration , Bol.com integration , inventory management , warehouse transfer module , dropship and dropshipper integration and other Odoo integration application or module, Odoo Magento2 Connector, Magento2 Connector, Magento2',
    # Author
    'author': 'Emipro Technologies Pvt. Ltd.',
    'website': 'http://www.emiprotechnologies.com/',
    'maintainer': 'Emipro Technologies Pvt. Ltd.',

    # Dependencies
    'depends': ['common_connector_library'],
    # Views
    'data': [
        'security/security.xml',
        'data/import_order_status.xml',
        'views/common_log_book_ept.xml',
        'wizard_views/magento_notification_ept.xml',
        'views/magento_instance_view.xml',
        'views/magento_website_view.xml',
        'views/magento_storeview_view.xml',
        'views/magento_inventory_locations_view.xml',
        'views/magento_payment_method_view.xml',
        'views/delivery_carrier_view.xml',
        'views/view_magento_process_log.xml',
        'wizard_views/magento_import_export_operation_view.xml',
        'wizard_views/magento_cron_configuration_view.xml',
        'wizard_views/res_config_magento_instance.xml',
        'wizard_views/res_config_settings.xml',
        'data/ir_sequence_data.xml',
        'wizard_views/magento_export_product_ept.xml',
        'views/magento_product_product_view.xml',
        'views/magento_product_template_view.xml',
        'views/magento_product_image_view.xml',
        'wizard_views/magento_queue_process_wizard_view.xml',
        'views/res_partner_view.xml',
        'views/sale_order_view.xml',
        'views/sale_order_cancel_view.xml',
        'views/order_queue.xml',
        'views/order_queue_line.xml',
        'views/product_queue.xml',
        'views/product_queue_line.xml',
        'views/customer_queue_ept.xml',
        'views/customer_queue_line_ept.xml',
        'views/export_stock_queue.xml',
        'views/export_stock_queue_line.xml',
        'data/magento_data_cron.xml',
        'data/ir_cron_data.xml',
        'data/ir_attachment_data.xml',
        'views/stock_picking_view.xml',
        'wizard_views/magento_export_credit_memo.xml',
        'views/account_move_view.xml',
        'views/magento_dashboard_view.xml',
        'views/financial_status_view.xml',
        'views/magento_delivery_carrier.xml',
        'views/magento_instances_onboarding_panel_view.xml',
        'views/magento_product_category_view.xml',
        'views/magento_tax_class.xml',
        'views/magento_attribute_set.xml',
        'views/magento_attribute_group.xml',
        'views/magento_attribute_option.xml',
        'views/magento_product_attribute_view.xml',
        'views/magento_order_status.xml',
        'wizard_views/magento_instance_configuration_wizard.xml',
        'wizard_views/basic_configuration_onboarding.xml',
        'wizard_views/financial_status_onboarding_view.xml',
        'wizard_views/magento_onboarding_confirmation_ept.xml',
        'data/ecommerce_data.xml',
        'security/ir.model.access.csv',
        'report/sale_report.xml'
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/odoo_magento2_ept/static/src/css/graph_widget_ept.scss',
            '/odoo_magento2_ept/static/src/js/magento_button_collapse.js',
            '/odoo_magento2_ept/static/src/js/magento_icon_view.js'
        ],
        # 'web.assets_qweb': [
        #     '/odoo_magento2_ept/static/src/xml/dashboard_widget.xml',
        # ]
    },

    # Odoo Store Specific

    'images': [
        'static/description/main_screenshot.gif',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'live_test_url': 'https://www.emiprotechnologies.com/free-trial?app=odoo-magento2-ept&version=15',
    'price': 379.00,
    'currency': 'EUR',

}
