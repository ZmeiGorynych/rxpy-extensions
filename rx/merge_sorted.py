from rx.core import Observable, AnonymousObservable
from rx.disposables import CompositeDisposable, SingleAssignmentDisposable
from rx.internal import extensionmethod, extensionclassmethod

@extensionmethod(Observable, instancemethod=True)
def merge_sorted(self, *args, **kwargs):
    """Merges two or more observable sequences, assumed to be ordered,
    into one ordered observable sequence, preserving all the elements.

    The sequences can be supplied as individual arguments or as a list.
    Comparison function is min by default, accepts custom ordering function
    as named argument selector.

    Once all non-completed sequences have produced at least one element,
    the vector of latest values is reduced using the selector function.
    The element thus selected is removed from its sequence and broadcast downstream,
    and the procedure is then repeated.

    1 - res = obs1.zip(obs2, obs3,..., obsN)
    2 - res = obs1.zip(obs2, obs3,..., obsN, selector=func)
    3 - res = obs1.zip([obs2, obs3,..., obsN])
    4 - res = obs1.zip([obs2, obs3,..., obsN], selector=func)

    Implementation loosely based on the RxPY zip function
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
    """Merges two or more observable sequences, assumed to be ordered,
    into one ordered observable sequence, preserving all the elements.

    The sequences can be supplied as individual arguments or as a list.
    Comparison function is min by default, accepts custom ordering function
    as named argument selector.

    Once all non-completed sequences have produced at least one element,
    the vector of latest values is reduced using the selector function.
    The element thus selected is removed from its sequence and broadcast downstream,
    and the procedure is then repeated.

    1 - res = Observable.zip(obs1, obs2,..., obsN)
    2 - res = Observable.zip(obs1, obs2,..., obsN, selector=func)
    3 - res = Observable.zip([obs1, obs2,..., obsN])
    4 - res = Observable.zip([obs1, obs2,..., obsN], selector=func)
    """

    if args and isinstance(args[0], list): # allow first arg to be a list of observables
        first=args[0].pop()
        return first.merge_sorted(*args,**kwargs)
    else:
        first = args[0]
        return first.merge_sorted(*args[1:],**kwargs)
