# Copyright 2017 Google Inc. All rights reserved.
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
r"""Sample server that pushes configuration to Google Cloud IoT devices.

This example represents a server that consumes telemetry data from multiple
Cloud IoT devices. The devices report telemetry data, which the server consumes
from a Cloud Pub/Sub topic. The server then decides whether to turn on or off
individual devices fans.

This example requires the Google Cloud Pub/Sub client library. Install it with

  $ pip install --upgrade google-cloud-pubsub

If you are running this example from a Compute Engine VM, you will have to
enable the Cloud Pub/Sub API for your project, which you can do from the Cloud
Console. Create a pubsub topic, for example
projects/my-project-id/topics/my-topic-name, and a subscription, for example
projects/my-project-id/subscriptions/my-topic-subscription.

You can then run the example with

  $ python cloudiot_pubsub_example_server.py \
    --project_id=my-project-id \
    --pubsub_topic=my-topic-name \
    --pubsub_subscription=my-topic-subscription \
    --api_key=YOUR_API_KEY
"""

import argparse
import base64
import json
import sys

from googleapiclient import discovery
from oauth2client.service_account import ServiceAccountCredentials

from google.cloud import pubsub

API_SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
API_VERSION = 'v1beta1'
DISCOVERY_API = 'https://cloudiot.googleapis.com/$discovery/rest'
SERVICE_NAME = 'cloudiot'


def discovery_url(api_key):
  """Construct the discovery url for the given api key."""
  return '{}?version={}&key={}'.format(DISCOVERY_API, API_VERSION, api_key)


class Server(object):
  """Represents the state of the server."""

  def __init__(self, service_account_json, api_key):
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        service_account_json, API_SCOPES)
    if not credentials:
      sys.exit('Could not load service account credential from {}'.format(
          service_account_json))

    self._service = discovery.build(
        SERVICE_NAME,
        API_VERSION,
        discoveryServiceUrl=discovery_url(api_key),
        credentials=credentials)

  def _update_device_config(self, project_id, region, registry_id, device_id,
                            data):
    """Push the data to the given device as configuration."""
    config_data = None
    if data['temperature'] < 0:
      # Turn off the fan.
      config_data = {'fan_on': False}
      print 'Setting fan state for device', device_id, 'to off.'
    elif data['temperature'] > 10:
      # Turn on the fan
      config_data = {'fan_on': True}
      print 'Setting fan state for device', device_id, 'to on.'
    else:
      # Temperature is OK, don't need to push a new config.
      return

    config_data_json = json.dumps(config_data)
    body = {
        # The device configuration specifies a version to update, which can be
        # used to avoid having configuration updates race. In this case, we
        # use the special value of 0, which tells Cloud IoT to always update the
        # config.
        'version_to_update': 0,
        'data': {
            # The data is passed as raw bytes, so we encode it as base64. Note
            # that the device will receive the decoded string, and so you do not
            # need to base64 decode the string on the device.
            'binary_data': base64.b64encode(config_data_json)
        }
    }

    device_name = 'projects/{}/locations/{}/registries/{}/devices/{}'.format(
        project_id, region, registry_id, device_id)

    request = self._service.projects().locations().registries().devices(
    ).modifyCloudToDeviceConfig(
        name=device_name, body=body)
    return request.execute()

  def run(self, project_id, pubsub_topic, pubsub_subscription):
    """The main loop for the device. Consume messages from the Pub/Sub topic."""
    pubsub_client = pubsub.Client(project=project_id)
    topic_name = 'projects/{}/topics/{}'.format(project_id, pubsub_topic)
    topic = pubsub_client.topic(topic_name)
    subscription = topic.subscription(pubsub_subscription)
    print 'Server running. Consuming telemetry events from', topic_name

    while True:
      # Pull from the subscription, waiting until there are messages.
      results = subscription.pull(return_immediately=False)
      for ack_id, message in results:
        data = json.loads(message.data)
        # Get the registry id and device id from the attributes. These are
        # automatically supplied by IoT, and allow the server to determine which
        # device sent the event.
        device_project_id = message.attributes['projectId']
        device_registry_id = message.attributes['deviceRegistryId']
        device_id = message.attributes['deviceId']
        device_region = message.attributes['deviceRegistryLocation']

        # Send the config to the device.
        self._update_device_config(device_project_id, device_region,
                                   device_registry_id, device_id, data)

      if results:
        # Acknowledge the consumed messages. This will ensure that they are not
        # redelivered to this subscription.
        subscription.acknowledge([ack_id for ack_id, message in results])


def parse_command_line_args():
  """Parse command line arguments."""
  parser = argparse.ArgumentParser(
      description='Example of Google Cloud IoT registry and device management.')
  # Required arguments
  parser.add_argument(
      '--project_id', required=True, help='GCP cloud project name.')
  parser.add_argument(
      '--pubsub_topic',
      required=True,
      help=('Google Cloud Pub/Sub topic name.'))
  parser.add_argument(
      '--pubsub_subscription',
      required=True,
      help='Google Cloud Pub/Sub subscription name.')
  parser.add_argument('--api_key', required=True, help='Your API key.')

  # Optional arguments
  parser.add_argument(
      '--service_account_json',
      default='service_account.json',
      help='Path to service account json file.')

  return parser.parse_args()


def main():
  args = parse_command_line_args()

  server = Server(args.service_account_json, args.api_key)
  server.run(args.project_id, args.pubsub_topic, args.pubsub_subscription)


if __name__ == '__main__':
  main()
