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

import unittest
import time
import json
from tests.base import SDKTestBase
import alibabacloud
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import DescribeInstancesRequest
from aliyunsdkcore.vendored.six import iteritems
from alibabacloud.services.ecs import ECSInstanceResource


class EcsResourceTest(SDKTestBase):

    def _instance_clean_up(self):
        ecs = self._get_ecs_resource()
        for inst in ecs.instances.all():
            if inst.status != inst.STATUS_STOPPED:
                inst.stop()

        for inst in ecs.instances.all():
            inst.wait_until(inst.STATUS_STOPPED)

        for inst in ecs.instances.all():
            inst.delete()

        print("waiting all instance to be deleted")
        while True:
            if len(list(ecs.instances.all())) == 0:
                break
        print("clean up finished")

    def setUp(self):
        self._instance_clean_up()

    def tearDown(self):
        self._instance_clean_up()

    def _get_ecs_resource(self):
        return alibabacloud.get_resource(
            'ecs',
            self.access_key_id,
            self.access_key_secret,
            self.region_id,
        )

    def status_verify(self, instance):
        request = DescribeInstancesRequest()
        request.set_InstanceIds(json.dumps([instance.instance_id]))
        response = self.client.do_action_with_exception(request)
        obj = json.loads(response.decode('utf-8'))['Instances']['Instance'][0]
        for key, value in iteritems(obj):
            attr_name = self._convert_camel_to_snake(key)
            self.assertTrue(hasattr(instance, attr_name), "instance has no " + attr_name)
            self.assertEqual(obj[key], getattr(instance, attr_name))

    def test_basic_instance_op(self):

        ecs = self._get_ecs_resource()
        instance = ecs.create_instance(
            ImageId="coreos_1745_7_0_64_30G_alibase_20180705.vhd",
            InstanceType="ecs.n2.small",
        )

        self.assertTrue(hasattr(instance, 'instance_id'))

        instance.start()
        instance.wait_until(instance.STATUS_RUNNING)
        instance.reboot()
        instance.wait_until(instance.STATUS_RUNNING)
        instance.stop()
        instance.wait_until(instance.STATUS_STOPPED)
        print("wait 60 to delete")
        time.sleep(60)
        instance.delete()

    def test_empty_instances(self):
        # Begin with no instance
        ecs = self._get_ecs_resource()
        self.assertEqual([], list(ecs.instances.all()))
        self.assertEqual([], list(ecs.instances.filter(InstanceType='ecs.g5.large')))
        self.assertEqual([], list(ecs.instances.limit(10)))
        self.assertEqual([], list(ecs.instances.page_size(5)))

    def _create_a_lot_instances(self):
        self._instance_clean_up()
        ecs = self._get_ecs_resource()

        starting_instances_to_wait = []
        for instance_type in ['ecs.n2.large', 'ecs.n2.small']:
            for i in range(7):
                ecs.create_instance(
                    ImageId="coreos_1745_7_0_64_30G_alibase_20180705.vhd",
                    InstanceType=instance_type,
                )

                instance = ecs.create_instance(
                    ImageId="coreos_1745_7_0_64_30G_alibase_20180705.vhd",
                    InstanceType=instance_type,
                )
                instance.start()
                starting_instances_to_wait.append(instance)

        for instance in starting_instances_to_wait:
            instance.wait_until(instance.STATUS_RUNNING)

    def test_instance_resource_collection(self):
        # self._create_a_lot_instances()

        ecs = self._get_ecs_resource()
        self._test_all()
        self._test_filter()
        self._test_limit()
        self._test_page_size()
        self._test_iterator_joint()

    def _get_ids(self, instance_iterable):
        return [i.instance_id for i in instance_iterable]

    def _test_all(self):
        ecs = self._get_ecs_resource()
        instances = list(ecs.instances.all())
        self.assertEqual(28, len(instances))
        instance_ids = self._get_ids(instances)
        self.assertEqual(28, len(set(instance_ids)))   # make sure all instance ids are identical
        for instance in instances:
            self.status_verify(instance)

    def _test_filter(self):
        ecs = self._get_ecs_resource()
        count = 0
        for instance in ecs.instances.filter(InstanceType='ecs.n2.large'):
            self.assertEqual(instance.instance_type, 'ecs.n2.large')
            count += 1
        self.assertEqual(14, count)

        count = 0
        for instance in ecs.instances.filter(Status=ECSInstanceResource.STATUS_RUNNING):
            self.assertEqual(instance.status, instance.STATUS_RUNNING)
            count += 1
        self.assertEqual(13, count)  # FIXME we started 14 instances, bug

        count = 0
        for instance in ecs.instances.filter(InstanceType='ecs.n2.large',
                                             Status=ECSInstanceResource.STATUS_RUNNING):
            self.assertEqual(instance.instance_type, 'ecs.n2.large')
            self.assertEqual(instance.status, instance.STATUS_RUNNING)
            count += 1
        self.assertEqual(7, count)

        all_ids = self._get_ids(ecs.instances.all())
        instance_id = all_ids[-1]
        instances = list(ecs.instances.filter(instance_id=instance_id))
        self.assertEqual(1, len(instances))
        self.assertEqual(instance_id, instances[0].instance_id)

        instance_ids = all_ids[:2]
        instances = list(ecs.instances.filter(instance_ids=instance_ids))
        self.assertEqual(2, len(instances))
        self.assertEqual(set(instance_ids), set(self._get_ids(instances)))

    def _test_limit(self):
        ecs = self._get_ecs_resource()
        self.assertEqual(7, len(list(ecs.instances.limit(7))))
        self.assertEqual(10, len(list(ecs.instances.limit(10))))
        self.assertEqual(13, len(list(ecs.instances.limit(13))))

        all_ids = self._get_ids(ecs.instances.all())
        self.assertEqual(all_ids[:7], self._get_ids(ecs.instances.limit(7)))

        for inst in ecs.instances.limit(7):
            self.status_verify(inst)

    def _test_page_size(self):
        ecs = self._get_ecs_resource()

        try:
            for i in ecs.instances.page_size(101):
                pass
            assert False
        except ServerException as e:
            self.assertEqual("InvalidParameter", e.get_error_code())

        all_ids = self._get_ids(ecs.instances.all())
        instances = list(ecs.instances.page_size(100))
        self.assertEqual(28, len(instances))
        self.assertEqual(all_ids, self._get_ids(instances))

        self.assertEqual(28, len(list(ecs.instances.page_size(28))))
        self.assertEqual(28, len(list(ecs.instances.page_size(7))))
        self.assertEqual(28, len(list(ecs.instances.page_size(13))))

    def _test_iterator_joint(self):
        ecs = self._get_ecs_resource()
        self.assertEqual(10, len(list(ecs.instances.page_size(28).limit(10))))
        self.assertEqual(28, len(list(ecs.instances.page_size(28).limit(30))))
        self.assertEqual(10, len(list(ecs.instances.limit(10).page_size(29))))
        self.assertEqual(28, len(list(ecs.instances.limit(30).page_size(2))))

        self.assertEqual(10, len(list(ecs.instances.limit(20).limit(10))))
        self.assertEqual(28, len(list(ecs.instances.page_size(28).page_size(100))))

        count = 0
        for inst in ecs.instances.page_size(5).limit(8).filter(InstanceType='ecs.n2.small'):
            count += 1
            self.assertEqual('ecs.n2.small', inst.instance_type)
        self.assertEqual(8, count)

        count = 0
        for inst in ecs.instances.filter(InstanceType='ecs.n2.large').filter(
                Status=ECSInstanceResource.STATUS_STOPPED):
            count += 1
            self.assertEqual('ecs.n2.large', inst.instance_type)
            self.assertEqual(ECSInstanceResource.STATUS_STOPPED, inst.status)
        self.assertEqual(7, count)


if __name__ == '__main__':
    unittest.main()

