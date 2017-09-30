import google.cloud
from google.cloud import pubsub


publisher = pubsub.PublisherClient()
subscriber = pubsub.SubscriberClient()

def pub(msg):
    msg_encode = msg
    print msg_encode
    print 'in pub',type(msg),type(msg_encode)
    pub_topic = 'projects/{project}/topics/{topic}'.format(project=project_id, topic=pubsub_topic_name)
    publisher.publish(pub_topic,msg_encode)



def sub():
    sub_topic = 'projects/{project}/subscriptions/{subscription}'.format(project=project_id,subscription=pubsub_subscription)
    subs = subscriber.subscribe(sub_topic)

    """def callback(message):
        print(message.data)
        message.ack()

    subs.open(callback)"""

    def receive_messages():
        """Receives messages from a pull subscription."""
        #subscriber = pubsub.SubscriberClient()
        subscription_path = subscriber.subscription_path(project_id, pubsub_subscription)

        def callback(message):
            print('Received message: {}'.format(message))
            message.ack()

        subscriber.subscribe(subscription_path, callback=callback)

        # The subscriber is non-blocking, so we must keep the main thread from
        # exiting to allow it to process messages in the background.
        print('Listening for messages on {}'.format(subscription_path))
        while True:
            time.sleep(60)



def variables():
    project_id = 'work-180507'
    project_name = 'work'
    pubsub_topic_name = 'data_viv'
    pubsub_subscription = 'data_fetch'
    api_key = 'AIzaSyA7xkmdcUrKgGpF41HKb279lCTxtuIszwg'
    globals().update(locals())


def main():
    variables()
    msg = str(raw_input('enter your msg :'))
    print type(msg)
    pub(msg)
    sub()                      #msg_r == message recieved by subscriber


if __name__ == '__main__':
    main()

