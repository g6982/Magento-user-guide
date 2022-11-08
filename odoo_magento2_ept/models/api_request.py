# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Requrests API to magento.
"""
import json
import logging
import socket
import requests
from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger("Magento EPT")


def req(instance, path, method='GET', data=None, params=None, is_raise=False):
    """
    This method use for base on API request it call API method.
    """
    location_url = check_location_url(instance.magento_url)
    verify_ssl = instance.magento_verify_ssl
    api_url = '{}{}'.format(location_url, path)
    headers = get_headers(instance.access_token)
    method = method.lower()
    if hasattr(requests, method):
        try:
            if verify_ssl:
                if data:
                    # We only pass the data variable as an argument for the GET request.
                    # If we all the data = '' as blank then also it gives an error from Magento end.
                    data = json.dumps(data)
                    response = getattr(requests, method)(url=api_url, headers=headers,
                                                         data=data, verify=True, params=params)
                else:
                    response = getattr(requests, method)(url=api_url, headers=headers,
                                                         verify=True, params=params)
            else:
                if data:
                    # We only pass the data variable as an argument for the GET request.
                    # If we all the data = '' as blank then also it gives an error from Magento end.
                    data = json.dumps(data)
                    response = getattr(requests, method)(url=api_url, headers=headers,
                                                         data=data, params=params)
                else:
                    response = getattr(requests, method)(url=api_url, headers=headers,
                                                         params=params)
            _logger.info(api_url)
        except (socket.gaierror, socket.error, socket.timeout) as error:
            raise UserError(_('A network error caused the failure of the job: %s', error))
        except Exception as error:
            message = get_common_error_message(str(error))
            raise UserError(_(message))
        return handle_response(response, is_raise)
    return dict()


def check_location_url(location_url):
    """
    Set Magento rest API URL
    :param location_url: Magento URL
    :return:
    """
    if location_url:
        location_url = location_url.strip()
        location_url = location_url.rstrip('/')
        location_vals = location_url.split('/')
        if location_vals[-1] != 'rest':
            location_url = location_url + '/rest'
    return location_url


def get_headers(token):
    return {
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'User-Agent': 'My User Agent 1.0',
        'Authorization': 'Bearer {}'.format(token)
    }


def handle_response(response, is_raise=False):
    if response.status_code in (200, 500):
        try:
            return response.json()
        except Exception as error:
            _logger.error(error)
    if response.status_code == 401:
        _logger.error(response)
        raise UserError('Given Credentials are incorrect, Kindly use correct Credentials.')
    elif response.status_code == 500:
        _logger.error(response)
        message = get_500_error_message()
        error = ''
        if isinstance(response, requests.models.Response):
            error = response.content.decode()
        elif isinstance(response, dict) and response.get('messages'):
            error = response.get('messages', '')
        message += '4. We got the following response from Magento API. \n{}'.format(error)
        if is_raise:
            raise UserError(_(message))
        else:
            return error
    else:
        _logger.error(response)
        message = get_common_error_message()
        raise UserError(_(message))


def get_500_error_message():
    return """
    We are getting internal server errors while sending request to Magento.
    This can be due to the following reasons.\n
    1. Permission issues.\n
    2. Memory Limitation.\n
    3. Third Party Plugin issue.\n
    """


def get_common_error_message(error=''):
    return """
    It is possible that the API request has not been satisfied for the following reasons:\n
    1. Access tokens can be incorrect or not configured properly: Magento2 admin panel 
    > System > Integration > API > Set 'All' in the Resource Access field. 
    Refer to the user guide for more details.\n
    2. There is no Emipro API change plugin installed on Magento2 or the plugin is not 
    updated correctly. Download the latest API change plugin from the instance wizard and 
    upload it on the Magento2 server. Please read the user guide on how to download and 
    upload the API change plugin.\n
    3. It's possible that Magento2 has blocked your IP address, for which you need to 
    whitelist it. Please contact your Magento2 support team for more information.
    {}
    """.format(error)


def create_filter(field, value, condition_type='eq'):
    """
    Create dictionary for filter.
    :param field: Field to be filter
    :param value: Value to be filter
    :param condition_type: condition type to be filter
    :return: Dictionary for filter
    """
    filter_dict = {'field': field}
    if isinstance(value, str) and condition_type == "in":
        filter_dict['condition_type'] = 'eq'
    elif isinstance(value, str) and condition_type == "like":
        filter_dict['condition_type'] = 'like'
    elif isinstance(value, str) and condition_type == "nin":
        filter_dict['condition_type'] = 'nlike'
    else:
        filter_dict['condition_type'] = condition_type
    filter_dict['value'] = value
    return filter_dict


def create_search_criteria(filters, **kwargs):
    """
        Create Search Criteria
        if filters is {'updated_at': {'to': '2016-12-22 10:42:44', 'from': '2016-12-16 10:42:18'}}
        then searchCriteria = {'searchCriteria': {'filterGroups': [{'filters': [{'field':
        'updated_at', 'condition_type': 'to', 'value': '2016-12-22 10:42:44'}]},{'filters':
        [{'field': 'updated_at', 'condition_type': 'from', 'value': '2016-12-16 10:42:18'}]}]}}
    """
    searchcriteria = {}
    if filters is None:
        filters = {}

    if not filters:
        searchcriteria = {
            'searchCriteria': {
                'filterGroups': [{
                    'filters': [{
                        'field': 'id', 'value': -1, 'condition_type': 'gt'
                    }]
                }]
            }
        }
    else:
        searchcriteria.setdefault('searchCriteria', {})
        filtersgroup_list = []
        for k, val in filters.items():
            tempfilters = {}
            filters_list = []
            if isinstance(val, dict):
                for operator, values in val.items():
                    filters_list, filtersgroup_list, tempfilters = generate_filter_groups(
                        operator, values, k, filters_list, tempfilters, filtersgroup_list)
            else:
                filters_list.append(create_filter(k, val))
                tempfilters["filters"] = filters_list
                filtersgroup_list.append(tempfilters)
        searchcriteria["searchCriteria"]['filterGroups'] = filtersgroup_list
        if kwargs.get('page_size', 0):
            searchcriteria.get('searchCriteria', dict()).update({'pageSize': kwargs.get('page_size')})
        if kwargs.get('page', 0):
            searchcriteria.get('searchCriteria', dict()).update({'currentPage': kwargs.get('page')})
        if kwargs.get('fields'):
            searchcriteria.update({'fields': ",".join(kwargs.get('fields'))})
    return searchcriteria


def generate_filter_groups(operator, values, k, filters_list, tempfilters, filtersgroup_list):
    if isinstance(values, list):
        if operator == "in":
            for value in values:
                filters_list.append(create_filter(k, value, operator))
            tempfilters["filters"] = filters_list
            filtersgroup_list.append(tempfilters)
        elif operator == "nin":
            for value in values:
                filters_list.append(create_filter(k, value, operator))
                tempfilters["filters"] = filters_list
                filtersgroup_list.append(tempfilters)
    else:
        filters_list.append(create_filter(k, values, operator))
        tempfilters["filters"] = filters_list
        filtersgroup_list.append(tempfilters)
        filters_list = []
        tempfilters = {}
    return filters_list, filtersgroup_list, tempfilters
