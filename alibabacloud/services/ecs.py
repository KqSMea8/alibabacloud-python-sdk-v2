# Copyright 2018 Alibaba Cloud Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import copy
import json

from aliyunsdkcore.client import AcsClient
from aliyunsdkecs.request.v20140526.CreateInstanceRequest import CreateInstanceRequest
from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import DescribeInstancesRequest
from aliyunsdkecs.request.v20140526.StartInstanceRequest import StartInstanceRequest
from aliyunsdkecs.request.v20140526.StopInstanceRequest import StopInstanceRequest
from aliyunsdkecs.request.v20140526.DeleteInstanceRequest import DeleteInstanceRequest
from aliyunsdkecs.request.v20140526.RunInstancesRequest import RunInstancesRequest
from aliyunsdkecs.request.v20140526.RebootInstanceRequest import RebootInstanceRequest
from aliyunsdkecs.request.v20140526.RenewInstanceRequest import RenewInstanceRequest
from aliyunsdkecs.request.v20140526.ReActivateInstancesRequest import ReActivateInstancesRequest
from aliyunsdkecs.request.v20140526.DescribeInstanceStatusRequest import DescribeInstanceStatusRequest


class ECSInstanceResource:

    def __init__(self, client=None, **kwargs):
        self.client = client
        self.instance_id = kwargs.get('InstanceId', None)
        self.instance_name = kwargs.get('InstanceName', None)
        self.host_name = kwargs.get('HostName', None)
        self._status = kwargs.get('Status', None)
        self.image_id = kwargs.get('ImageId', None)
        self.vlan_id = kwargs.get('VlanId', None)
        self.inner_ip_address = kwargs.get('InnerIpAddress', None)
        self.instance_type_family = kwargs.get('InstanceTypeFamily', None)
        self.eip_address = kwargs.get('EipAddress', None)
        self.internet_max_bandwidth_in = kwargs.get('InternetMaxBandwidthIn', None)
        self.creditSpecification = kwargs.get('CreditSpecification', None)
        self.zone_id = kwargs.get('ZoneId', None)
        self.internet_charge_type = kwargs.get('InternetChargeType', None)
        self.spot_strategy = kwargs.get('SpotStrategy', None)
        self.stopped_mode = kwargs.get('StoppedMode', None)
        self.stopped_mode = kwargs.get('SerialNumber', None)


    def __getitem__(self, item):
        return getattr(self, item, None)

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    @property
    def status(self):
        request = DescribeInstanceStatusRequest()
        response = self.client.do_action_with_exception(request)
        response = json.loads(response.decode('utf-8'))
        status = response.get('InstanceStatuses')
        for item in status.get('InstanceStatus'):
            if item.get('InstanceId') == self.instance_id:
                self._status = item.get('Status')
        return self._status

    def start(self):
        request = StartInstanceRequest()
        request.set_InstanceId(self.instance_id)
        self.client.do_action_with_exception(request)

    def stop(self):
        request = StopInstanceRequest()
        request.set_InstanceId(self.instance_id)
        self.client.do_action_with_exception(request)

    def reboot(self):
        request = RebootInstanceRequest()
        request.set_InstanceId(self.instance_id)
        self.client.do_action_with_exception(request)

    def delete(self):
        request = DeleteInstanceRequest()
        request.set_InstanceId(self.instance_id)
        self.client.do_action_with_exception(request)

    def renew(self, **kwargs):
        request = RenewInstanceRequest()
        request.set_InstanceId(self.instance_id)
        for key, value in kwargs.items():
            if hasattr(request, 'set_'+key):
                func = getattr(request, 'set_' + key)
                func(value)
        self.client.do_action_with_exception(request)

    def reactivate(self, **kwargs):
        request = ReActivateInstancesRequest()
        request.set_InstanceId(self.instance_id)
        for key, value in kwargs.items():
            if hasattr(request, 'set_' + key):
                func = getattr(request, 'set_' + key)
                func(value)
        self.client.do_action_with_exception(request)


class ResourceCollection:

    def __init__(self, client=None, **kwargs):
        self.client = client
        self._params = kwargs
        self.page_size = kwargs.get('page_size', 100)

    def __repr__(self):
        # <QuerySet [{'name__lower': 'beatles blog'}]>
        return '<{0} {1}>'.format(self.__class__.__name__, list(self))

    def __iter__(self):
        params = copy.deepcopy(self._params)
        limit = params.pop('limit', None)
        params.pop('page_size', None)
        count = 0
        for page in self.pages():
            for item in page:
                if params:
                    for key, value in params.items():
                        if value == item[key]:
                            yield item
                else:
                    yield item
                    count += 1
                    if limit is not None and count >= limit:
                        return

    def handler_desc_instance_request(self, page_num=1):
        request = DescribeInstancesRequest()
        request.set_PageSize(self.page_size)
        request.set_PageNumber(page_num)
        response = self.client.do_action_with_exception(request)
        response_obj = json.loads(response.decode('utf-8'))
        return response_obj

    def pages(self):
        response_obj = self.handler_desc_instance_request()
        total = response_obj.get('TotalCount')
        quotient, remainder = divmod(total, self.page_size)
        if remainder > 0:
            quotient += 1
        for i in range(1, quotient + 1):
            response_obj = self.handler_desc_instance_request(page_num=i)
            instances = response_obj.get('Instances')['Instance']
            page_items = []
            for instance in instances:
                ecs_obj = ECSInstanceResource(client=self.client, **instance)
                page_items.append(ecs_obj)
            yield page_items


class ECSInstancesResource:
    _collection_cls = ResourceCollection

    def __init__(self, client):
        self.client = client

    def _iterator(self, **kwargs):
        return self._collection_cls(self.client, **kwargs)

    def all(self):
        return self._iterator()

    def filter(self, **kwargs):
        return self._iterator(**kwargs)

    def limit(self, count):
        if isinstance(count, int) and int(count) > 0:
            return self._iterator(limit=count)
        raise ValueError("The params of limit must be positive integers")

    def page_size(self, count=None):
        if isinstance(count, int) and int(count) > 0:
            return self._iterator(page_size=count)
        raise ValueError("The params of page_size must be positive integers")

    def pages(self):
        return self._iterator().pages()


class ECSClient:

    # TODO decide whether we actually need a client level like this

    def create_instance(self, **kwargs):
        request = CreateInstanceRequest()
        param = kwargs.get('ResourceOwnerId')
        if param is not None:
            request.set_ResourceOwnerId(param)
        self.do_request(request)

    def do_request(self, request):
        pass


class ECSResource:

    def __init__(self, access_key_id=None, access_key_secret=None, region_id=None):
        self._raw_client = AcsClient(access_key_id, access_key_secret, region_id)
        self.instances = ECSInstancesResource(self._raw_client)
        # self.client = ECSClient()

    def create_instance(self, **kwargs):
        # one+stop
        request = CreateInstanceRequest()
        for key, value in kwargs.items():
            if hasattr(request, 'set_'+key):
                func = getattr(request, 'set_' + key)
                func(value)
        response = self._raw_client.do_action_with_exception(request)
        return response

    def run_instances(self, **kwargs):
        # many+running
        request = RunInstancesRequest()
        for key, value in kwargs.items():
            if hasattr(request, 'set_'+key):
                func = getattr(request, 'set_' + key)
                func(value)
        response = self._raw_client.do_action_with_exception(request)
        return response


