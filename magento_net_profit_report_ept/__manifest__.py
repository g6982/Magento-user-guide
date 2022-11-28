# -*- coding: utf-8 -*-
{
    'name': "Magento Net Profit Report Ept",

    'summary': """
        Visible Net Profit report for magento all instances.""",

    'description': """
        Visible Net Profit report for magento all instances.
    """,

    'author': "Emipro Technologies Pvt. Ltd.",
    'website': "http://www.emiprotechnologies.com",

    'license': 'OPL-1',
    'category': 'Account',
    'version': '0.1',

    'depends': ['account_reports', 'odoo_magento2_ept'],

    'data': [
    
        'data/net_profit_report_data.xml',
        'report/net_profit_report.xml',
    ],
}
