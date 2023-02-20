from collections import defaultdict
from math import nan

from matsim import event_reader

class Parser():
    """Abstract base class for parsing of simulation output"""
    def __init__(self, filepath: str, options: list, **kwargs) -> None:
        pass
    def time_split(interval: list[float] | list[list[float]] | float | int):
        pass

class MATSimParser(Parser):
    """Convenience class to parse MATSim XML events output while allowing for time interval specification. Makes use of events parser from the matsim module"""
    def __init__(self, filepath: str, **kwargs) -> None:
        super().__init__(filepath, options)
        events = event_reader(filepath, kwargs.setdefault('types', None))
        events = self.time_split(events, kwargs['interval'])

    def link_counts(self, events, intervals: tuple[float] | list[tuple[float]] | float | int):
        """Aggregate link counts by specified interval"""

        if (isinstance(intervals, (float, int))):
            intervals = self.time_split(events, intervals)

        link_counts = defaultdict(defaultdict(int))
        # link_counts = {}

        # User specified only one interval
        if isinstance(intervals, tuple(float)):
            for event in events:
                if intervals(0) <= event['time'] < intervals(1):
                    link_counts[intervals][event['link']] += 1
                    # link_counts.setdefault(intervals, {}).setdefault(event['link'], 0)[event['link']] += 1

        # User specified multiple intervals
        if isinstance(intervals, list[tuple[float]]):
            for event in events:
                for interval in intervals:
                    if interval(0) <= event['time'] <= interval(1):
                        link_counts[event['link']] += 1


    def time_split(self, events, split: float | int):
        intervals = []

        times = [event.setdefault('time', nan) for event in events]
        start, end = min(times), max(times)

        # User specified the number of intervals to be constructed
        if isinstance(split, int):
            split = (end - start)/float(split)
        
        # User specified the duration of each interval (interval_start - interval_end)
        if isinstance(split, float):    
            pass

        while start <= end:
            intervals.append((start, start + split))
            start += split

        return intervals
            

class SUMOParser(Parser):
    def __init__(self, filepath: str, options: list, **kwargs) -> None:
        super().__init__(filepath, options)