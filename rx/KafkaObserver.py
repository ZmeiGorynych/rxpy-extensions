import rx
from rx import Observable, Observer

class KafkaObserver(Observer):
    def __init__(self, producer, topic):
        self.producer=producer
        self.topic=topic

    def on_next(self, x):
        self.producer.send(self.topic,x)

    def on_error(self, e):
        print("Got error: %s" % e)

    def on_completed(self):
        print("Sequence completed")
        print(self)

    def set_encoder(self, fun):
        self.encoder=fun