from rx.core import Observable, AnonymousObservable
from rx.disposables import CompositeDisposable, SingleAssignmentDisposable
from rx.internal import extensionmethod, extensionclassmethod

# tomorrow: change syntax to: accept list of sequences and comma-separated sequences;
# make min the default comparator
# how does backpressure work here?

@extensionmethod(Observable, instancemethod=True)
def merge_sorted(self, *args, **kwargs):
    """Merges the specified observable sequences into one observable
    sequence by using the selector function whenever all of the observable
    sequences or an array have produced an element at a corresponding index.

    The element thus selected is removed from its corresponding sequence,
    and the procedure is then repeated. Thus if you use 'min' as the selector
    function, and sorted_merge two sequences sorted in ascending order
    (eg by timestamp), the resulting sequence will also be sorted by ascending order

    If two elements from two sequences are equal, the function will first emit the one
    from the sequence that came first in the argument list

    The last element in the arguments must be a function to invoke for each
    series of elements at corresponding indexes in the sources.

    1 - res = obs1.zip(obs2, obs3,..., obsN, fn)

    Returns an observable sequence containing the result of combining
    elements of the sources using the specified result selector function.
    """

    parent = self
    sources = list(args)

    if sources and isinstance(sources[0], list):  # allow first arg to be a list of observables
        sources = sources[0] + sources[1:]

    sources.insert(0, parent)

    if 'selector' in kwargs:
        result_selector=kwargs['selector']
    else:
        result_selector=min


    def subscribe(observer):
        n = len(sources)
        queues = [[] for _ in range(n)]
        is_done = [False] * n
        latest = [[]] # latest value of each input
        def next():
            nonempty_not_done = [len(queues[e])>0 for e in range(len(queues)) if not is_done[e]]
            nonempty_ind=[e for e in range(len(queues)) if queues[e]]
            if all(nonempty_not_done): # if have values for all non-done queues, ie not waiting for a value
                try:
                    # extract latest values for non-finished sequences
                    latest = [queues[e][0] for e in nonempty_ind]
                    if len(latest)==0:
                        observer.on_completed()
                        return
                    elif len(latest)==1:
                        res=latest[0]
                    else:
                        res = reduce(result_selector,latest)
                    # find the index of the result in the latest vector, use first if several
                    ind=[e for e in range(len(latest)) if res==latest[e]][0]
                    queues[nonempty_ind[ind]].pop(0) # remove the chosen value from its queue
                    assert(res == latest[ind])
                except Exception as ex:
                    observer.on_error(ex)
                    return

                observer.on_next(res)

        def done(i): # keep track of completion of individual sequences.
            is_done[i] = True
            if all(is_done): # as long as we have cached values remaining, spool them out
                while not all( not q for q  in queues):
                    next()
                observer.on_completed()

        subscriptions = [None]*n

        def func(i): # subscribe to the ith input
            source = sources[i]
            sad = SingleAssignmentDisposable()
            source = Observable.from_future(source)

            def on_next(x):
                queues[i].append(x)
                next()

            sad.disposable = source.subscribe(on_next, observer.on_error, lambda: done(i))
            subscriptions[i] = sad
        for idx in range(n):
            func(idx)
        return CompositeDisposable(subscriptions)
    return AnonymousObservable(subscribe)


@extensionclassmethod(Observable)
def merge_sorted(cls, *args,**kwargs):
    """Merges the specified observable sequences into one observable
    sequence by using the selector function whenever all of the observable
    sequences have produced an element at a corresponding index.

    The last element in the arguments must be a function to invoke for each
    series of elements at corresponding indexes in the sources.

    Arguments:
    args -- Observable sources.

    Returns an observable {Observable} sequence containing the result of
    combining elements of the sources using the specified result selector
    function.
    """
    if args and isinstance(args[0], list): # allow first arg to be a list of observables
        first=args[0].pop()
        return first.merge_sorted(*args,**kwargs)
    else:
        first = args[0]
        return first.merge_sorted(*args[1:],**kwargs)
