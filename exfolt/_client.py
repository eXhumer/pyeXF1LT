from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta
from json import loads
from queue import Queue
from typing import Any, Dict, List, Tuple, Union

from requests import Session

from ._signalr import SignalRClient
from ._utils import decompress_zlib_data, timedelta_parser
from ._type import (
    ArchiveStatus,
    AudioStreams,
    BestSector,
    BestSpeeds,
    ContentStreams,
    CurrentTyres,
    Driver,
    ExtrapolatedClock,
    Hub,
    LapCount,
    PersonalBestLapTime,
    RaceControlMessages,
    SessionData,
    SessionInfo,
    SessionStatus,
    StreamingStatus,
    StreamingTopic,
    TeamRadio,
    TimingAppData,
    TimingBestLapTime,
    TimingData,
    TimingIntervalData,
    TimingLastLapTime,
    TimingSector,
    TimingSegment,
    TimingSpeeds,
    TimingStats,
    TimingStatsLine,
    TimingStint,
    TrackStatus,
    WeatherData,
)


class F1ArchiveClient:
    """
    F1 client to receive SignalR messages from an archived session
    """

    STATIC_URL = "https://livetiming.formula1.com/static"

    def __init__(self, path: str, *topics: StreamingTopic, session: Session | None = None):
        if not session:
            session = Session()

        res = session.get(f"{F1ArchiveClient.STATIC_URL}/{path}ArchiveStatus.json")
        res.raise_for_status()

        archive_status: ArchiveStatus = loads(res.content.decode("utf-8-sig"))
        status = archive_status["Status"]
        assert status == "Complete", f"Unexpected archive status \"{status}\"!"

        self.__path = path
        self.__topics = topics
        self.__session = session
        self.__data_queue: Queue[Tuple[StreamingTopic, Dict[str, Any], timedelta]] = Queue()
        self.__load_data()

    def __iter__(self):
        return self

    def __next__(self):
        if self.__data_queue.qsize() == 0:
            raise StopIteration

        return self.__data_queue.get()

    def __load_data(self):
        data_entries: List[Tuple[StreamingTopic, Dict[str, Any], timedelta]] = []

        for topic in self.__topics:
            res = self.__session.get(
                "".join((
                    f"{F1ArchiveClient.STATIC_URL}/{self.__path}",
                    f"{str(topic)}.jsonStream",
                )),
            )
            res.raise_for_status()

            if not topic.endswith(".z"):
                data_entries.extend([
                    (topic, loads(data_entry[12:]), timedelta_parser(data_entry[:12]))
                    for data_entry
                    in res.content.decode(encoding="utf-8-sig").replace("\r", "").split("\n")
                    if len(data_entry) > 0
                ])

            else:
                data_entries.extend([
                    (
                        topic,
                        loads(decompress_zlib_data(data_entry[13:-1])),
                        timedelta_parser(data_entry[:12])
                    )
                    for data_entry
                    in res.content.decode(encoding="utf-8-sig").replace("\r", "").split("\n")
                    if len(data_entry) > 0
                ])

        data_entries.sort(key=lambda entry: entry[2])

        for data_entry in data_entries:
            self.__data_queue.put(data_entry)

    @classmethod
    def get_session(
        cls,
        event_name: str,
        event_date: date,
        session_name: str,
        session_date: date,
        *topics: StreamingTopic,
        session: Session | None = None,
    ):
        if not session:
            session = Session()

        path = "/".join((
            str(event_date.year),
            "_".join((
                event_date.strftime("%Y-%m-%d"),
                event_name.replace(" ", "_"),
            )),
            "_".join((
                session_date.strftime("%Y-%m-%d"),
                session_name.replace(" ", "_"),
            )),
        )) + "/"

        return cls(path, *topics, session=session)

    @classmethod
    def get_last_session(cls, *topics: StreamingTopic, session: Session | None = None):
        if not session:
            session = Session()

        res = session.get(f"{F1ArchiveClient.STATIC_URL}/StreamingStatus.json")
        res.raise_for_status()
        streaming_status = loads(res.content.decode("utf-8-sig"))
        assert streaming_status["Status"] == "Offline", "Use F1LiveClient class for live sessions!"

        res = session.get(f"{F1ArchiveClient.STATIC_URL}/SessionInfo.json")
        res.raise_for_status()
        session_info = loads(res.content.decode("utf-8-sig"))

        return cls(session_info["Path"], *topics, session=session)


class F1LiveClient(SignalRClient):
    """
    F1 client to receive SignalR messages from a live session
    """

    URL = "https://livetiming.formula1.com/signalr"

    def __init__(self, *topics: StreamingTopic, reconnect: bool = True):
        self.__topics = topics
        super().__init__(F1LiveClient.URL, Hub.STREAMING, reconnect=reconnect)

    def __enter__(self):
        super().__enter__()
        self.invoke(Hub.STREAMING, "Subscribe", self.__topics)
        return self

    def __exit__(self, *args):
        if self.connected:
            self.invoke(Hub.STREAMING, "Unsubscribe", self.__topics)

        super().__exit__()

    @staticmethod
    def streaming_status():
        res = Session().get(f"{F1ArchiveClient.STATIC_URL}/StreamingStatus.json")
        res.raise_for_status()
        data: StreamingStatus = loads(res.content.decode("utf-8-sig"))
        return data["Status"]


class F1TimingClient:
    def __init__(self):
        self.__archive_status: ArchiveStatus | None = None
        self.__audio_streams: AudioStreams | None = None
        self.__car_data = None
        self.__content_streams: ContentStreams | None = None
        self.__current_tyres: CurrentTyres | None = None
        self.__driver_list: Dict[str, Driver] | None = None
        self.__extrapolated_clock: ExtrapolatedClock | None = None
        self.__lap_count: LapCount | None = None
        self.__position = None
        self.__race_control_messages: RaceControlMessages | None = None
        self.__session_data: SessionData | None = None
        self.__session_info: SessionInfo | None = None
        self.__session_status: SessionStatus | None = None
        self.__team_radio: TeamRadio | None = None
        self.__timing_app_data: TimingAppData | None = None
        self.__timing_data: TimingData | None = None
        self.__timing_stats: TimingStats | None = None
        self.__track_status: TrackStatus | None = None
        self.__weather_data: WeatherData | None = None

    def process_replay(self, old_data: Dict[StreamingTopic, Any]):
        if StreamingTopic.ARCHIVE_STATUS in old_data:
            archive_status: ArchiveStatus = old_data[StreamingTopic.ARCHIVE_STATUS]
            self.__archive_status = archive_status

        if StreamingTopic.AUDIO_STREAMS in old_data:
            audio_streams: AudioStreams = old_data[StreamingTopic.AUDIO_STREAMS]
            self.__audio_streams = audio_streams

        if StreamingTopic.CAR_DATA_Z in old_data:
            pass

        if StreamingTopic.CONTENT_STREAMS in old_data:
            content_streams: ContentStreams = old_data[StreamingTopic.CONTENT_STREAMS]
            self.__content_streams = content_streams

        if StreamingTopic.CURRENT_TYRES in old_data:
            current_tyres: CurrentTyres = old_data[StreamingTopic.CURRENT_TYRES]
            self.__current_tyres = current_tyres

        if StreamingTopic.DRIVER_LIST in old_data:
            drivers: Dict[str, Driver] = old_data[StreamingTopic.DRIVER_LIST]
            self.__driver_list = drivers

        if StreamingTopic.EXTRAPOLATED_CLOCK in old_data:
            extrapolated_clock: ExtrapolatedClock = \
                old_data[StreamingTopic.EXTRAPOLATED_CLOCK]
            self.__extrapolated_clock = extrapolated_clock

        if StreamingTopic.LAP_COUNT in old_data:
            lap_count: LapCount = old_data[StreamingTopic.LAP_COUNT]
            self.__lap_count = lap_count

        if StreamingTopic.POSITION_Z in old_data:
            pass

        if StreamingTopic.RACE_CONTROL_MESSAGES in old_data:
            race_control_messages: RaceControlMessages = \
                old_data[StreamingTopic.RACE_CONTROL_MESSAGES]
            self.__race_control_messages = race_control_messages

        if StreamingTopic.SESSION_DATA in old_data:
            session_data: SessionData = old_data[StreamingTopic.SESSION_DATA]
            self.__session_data = session_data

        if StreamingTopic.SESSION_INFO in old_data:
            session_info: SessionInfo = old_data[StreamingTopic.SESSION_INFO]
            self.__session_info = session_info

        if StreamingTopic.SESSION_STATUS in old_data:
            session_status: SessionStatus = old_data[StreamingTopic.SESSION_STATUS]
            self.__session_status = session_status

        if StreamingTopic.TEAM_RADIO in old_data:
            team_radio: TeamRadio = old_data[StreamingTopic.TEAM_RADIO]
            self.__team_radio = team_radio

        if StreamingTopic.TIMING_APP_DATA in old_data:
            timing_app_data: TimingAppData = old_data[StreamingTopic.TIMING_APP_DATA]
            self.__timing_app_data = timing_app_data

        if StreamingTopic.TIMING_DATA in old_data:
            timing_data: TimingData = old_data[StreamingTopic.TIMING_DATA]
            self.__timing_data = timing_data

        if StreamingTopic.TIMING_STATS in old_data:
            timing_stats: TimingStats = old_data[StreamingTopic.TIMING_STATS]
            self.__timing_stats = timing_stats

        if StreamingTopic.TRACK_STATUS in old_data:
            track_status: TrackStatus = old_data[StreamingTopic.TRACK_STATUS]
            self.__track_status = track_status

        if StreamingTopic.WEATHER_DATA in old_data:
            weather_data: WeatherData = old_data[StreamingTopic.WEATHER_DATA]
            self.__weather_data = weather_data

    def process_update(self, topic: StreamingTopic, update_data: dict,
                       timestamp: Union[datetime, timedelta]):
        if topic == StreamingTopic.ARCHIVE_STATUS:
            archive_status: ArchiveStatus = update_data

            if self.__archive_status is None:
                self.__archive_status = archive_status

            else:
                self.__archive_status |= archive_status

        elif topic == StreamingTopic.AUDIO_STREAMS:
            audio_streams: AudioStreams = update_data

            if isinstance(audio_streams["Streams"], Mapping):
                assert self.__audio_streams is not None

                for stream in audio_streams["Streams"].values():
                    self.__audio_streams["Streams"].append(stream)

            else:
                self.__audio_streams = audio_streams

        elif topic == StreamingTopic.CAR_DATA_Z:
            pass

        elif topic == StreamingTopic.CONTENT_STREAMS:
            content_streams: ContentStreams = update_data

            if isinstance(content_streams["Streams"], Mapping):
                assert self.__content_streams is not None

                for stream in content_streams["Streams"].values():
                    self.__content_streams["Streams"].append(stream)

            else:
                self.__content_streams = content_streams

        elif topic == StreamingTopic.CURRENT_TYRES:
            current_tyres: CurrentTyres = update_data

            if self.__current_tyres is None:
                self.__current_tyres = current_tyres

            else:
                for rn, driver_current_tyre in current_tyres["Tyres"].items():
                    if rn in self.__current_tyres["Tyres"]:
                        self.__current_tyres["Tyres"][rn] |= driver_current_tyre

                    else:
                        self.__current_tyres["Tyres"][rn] = driver_current_tyre

        elif topic == StreamingTopic.DRIVER_LIST:
            driver_list: Dict[str, Driver] = update_data

            if self.__driver_list is None:
                self.__driver_list = driver_list

            else:
                for rn, driver_data in driver_list.items():
                    if rn in self.__driver_list:
                        self.__driver_list[rn] |= driver_data

                    else:
                        self.__driver_list[rn] = driver_data

        elif topic == StreamingTopic.EXTRAPOLATED_CLOCK:
            extrapolated_clock: ExtrapolatedClock = update_data

            if self.__extrapolated_clock is None:
                self.__extrapolated_clock = extrapolated_clock

            else:
                self.__extrapolated_clock |= extrapolated_clock

        elif topic == StreamingTopic.LAP_COUNT:
            lap_count: LapCount = update_data

            if self.__lap_count is None:
                self.__lap_count = lap_count

            else:
                self.__lap_count |= lap_count

        elif topic == StreamingTopic.POSITION_Z:
            pass

        elif topic == StreamingTopic.RACE_CONTROL_MESSAGES:
            race_control_messages: RaceControlMessages = update_data

            if isinstance(race_control_messages["Messages"], Mapping):
                assert self.__race_control_messages is not None

                for message in race_control_messages["Messages"].values():
                    self.__race_control_messages["Messages"].append(message)

            else:
                self.__race_control_messages = race_control_messages

        elif topic == StreamingTopic.SESSION_DATA:
            session_data: SessionData = update_data

            if "Series" in session_data and "StatusSeries" in session_data:
                self.__session_data = session_data

            elif "Series" in session_data:
                assert self.__session_data is not None and \
                    isinstance(session_data["Series"], Mapping)

                for series_data in session_data["Series"].values():
                    self.__session_data["Series"].append(series_data)

            elif "StatusSeries" in session_data:
                assert self.__session_data is not None and \
                    isinstance(session_data["StatusSeries"], Mapping)

                for status_series_data in session_data["StatusSeries"].values():
                    self.__session_data["StatusSeries"].append(status_series_data)

        elif topic == StreamingTopic.SESSION_INFO:
            session_info: SessionInfo = update_data

            if "ArchiveStatus" in session_info and len(session_info) == 1:
                assert self.__session_info is not None
                self.__session_info["ArchiveStatus"] |= session_info["ArchiveStatus"]

            else:
                self.__session_info = session_info

        elif topic == StreamingTopic.SESSION_STATUS:
            session_status: SessionStatus = update_data

            if self.__session_status is None:
                self.__session_status = session_status

            else:
                self.__session_status |= session_status

        elif topic == StreamingTopic.TEAM_RADIO:
            team_radio: TeamRadio = update_data

            if isinstance(team_radio["Captures"], Mapping):
                assert self.__team_radio is not None

                for capture in team_radio["Captures"].values():
                    self.__team_radio["Captures"].append(capture)

            else:
                self.__team_radio = team_radio

        elif topic == StreamingTopic.TIMING_APP_DATA:
            timing_app_data: TimingAppData = update_data
            stints: Dict[str, Dict[str, TimingStint] | List[TimingStint]] = {}

            rns = list(timing_app_data["Lines"].keys())

            for rn in rns:
                if "Stints" in timing_app_data["Lines"][rn]:
                    driver_stints: Dict[str, TimingStint] | List[TimingStint] = \
                        timing_app_data["Lines"][rn].pop("Stints")

                    stints |= {rn: driver_stints}

            if self.__timing_app_data is None:
                self.__timing_app_data = timing_app_data

            else:
                for rn, timing_driver_app_data in timing_app_data["Lines"].items():
                    self.__timing_app_data["Lines"][rn] |= timing_driver_app_data

            for rn, driver_stints in stints.items():
                if "Stints" not in self.__timing_app_data["Lines"][rn]:
                    assert isinstance(driver_stints, Sequence)
                    self.__timing_app_data["Lines"][rn]["Stints"] = driver_stints

                else:
                    assert isinstance(driver_stints, Mapping)
                    assert isinstance(self.__timing_app_data["Lines"][rn]["Stints"], Sequence)

                    for sn, stint in driver_stints.items():
                        if int(sn) < len(self.__timing_app_data["Lines"][rn]["Stints"]):
                            self.__timing_app_data["Lines"][rn]["Stints"][int(sn)].update(stint)

                        else:
                            self.__timing_app_data["Lines"][rn]["Stints"].append(stint)

        elif topic == StreamingTopic.TIMING_DATA:
            timing_data: TimingData = update_data
            timing_dict_data: Dict[
                str,
                Tuple[
                    TimingIntervalData | None,
                    Dict[str, TimingSector] | List[TimingSector] | None,
                    TimingSpeeds | None,
                    TimingBestLapTime | None,
                    TimingLastLapTime | None,
                ],
            ] = {}

            rns = list(timing_data["Lines"].keys())

            for rn in rns:
                if "IntervalToPositionAhead" in timing_data["Lines"][rn]:
                    itpa: TimingIntervalData = \
                        timing_data["Lines"][rn].pop("IntervalToPositionAhead")

                else:
                    itpa = None

                if "Sectors" in timing_data["Lines"][rn]:
                    sectors: Dict[str, TimingSector] | List[TimingSector] = \
                        timing_data["Lines"][rn].pop("Sectors")

                else:
                    sectors = None

                if "Speeds" in timing_data["Lines"][rn]:
                    speeds: TimingSpeeds = timing_data["Lines"][rn].pop("Speeds")

                else:
                    speeds = None

                if "BestLapTime" in timing_data["Lines"][rn]:
                    blt: TimingBestLapTime = timing_data["Lines"][rn].pop("BestLapTime")

                else:
                    blt = None

                if "LastLapTime" in timing_data["Lines"][rn]:
                    llt: TimingLastLapTime = timing_data["Lines"][rn].pop("LastLapTime")

                else:
                    llt = None

                timing_dict_data |= {rn: (itpa, sectors, speeds, blt, llt)}

            if self.__timing_data is None:
                self.__timing_data = timing_data

            else:
                for rn in timing_data["Lines"].keys():
                    self.__timing_data["Lines"][rn] |= timing_data["Lines"][rn]

            for rn, dd in timing_dict_data.items():
                (itpa, sectors, speeds, blt, llt) = dd

                if itpa is not None:
                    if "IntervalToPositionAhead" not in self.__timing_data["Lines"][rn]:
                        self.__timing_data["Lines"][rn]["IntervalToPositionAhead"] = itpa

                    else:
                        self.__timing_data["Lines"][rn]["IntervalToPositionAhead"] |= itpa

                if sectors is not None:
                    if isinstance(sectors, Sequence):
                        self.__timing_data["Lines"][rn]["Sectors"] = sectors

                    else:
                        for sn, sd in sectors.items():
                            segments = None

                            if "Segments" in sd:
                                segments: Dict[str, TimingSegment] | List[TimingSegment] = \
                                    sd.pop("Segments")

                            self.__timing_data["Lines"][rn]["Sectors"][int(sn)] |= sd

                            if segments is not None:
                                if isinstance(segments, Mapping):
                                    for seg_num, seg_data in segments.items():
                                        self_sectors = self.__timing_data["Lines"][rn]["Sectors"]
                                        self_sectors[int(sn)]["Segments"][int(seg_num)] |= \
                                            seg_data

                                else:
                                    self_sectors = self.__timing_data["Lines"][rn]["Sectors"]
                                    self_sectors[int(sn)]["Segments"] = segments

                if speeds is not None:
                    if (
                        "Speeds" not in self.__timing_data["Lines"][rn] or
                        isinstance(speeds, Sequence)
                    ):
                        self.__timing_data["Lines"][rn]["Speeds"] = speeds

                    else:
                        for key, speed_data in speeds.items():
                            if key not in self.__timing_data["Lines"][rn]["Speeds"]:
                                self.__timing_data["Lines"][rn]["Speeds"][key] = speed_data

                            else:
                                self.__timing_data["Lines"][rn]["Speeds"][key] |= speed_data

                if blt is not None:
                    if "BestLapTime" not in self.__timing_data["Lines"][rn]:
                        self.__timing_data["Lines"][rn]["BestLapTime"] = blt

                    else:
                        self.__timing_data["Lines"][rn]["BestLapTime"] |= blt

                if llt is not None:
                    if "LastLapTime" not in self.__timing_data["Lines"][rn]:
                        self.__timing_data["Lines"][rn]["LastLapTime"] = llt

                    else:
                        self.__timing_data["Lines"][rn]["LastLapTime"] |= llt

        elif topic == StreamingTopic.TIMING_STATS:
            timing_stats: TimingStats = update_data

            lines = None

            if "Lines" in timing_stats:
                lines: Dict[str, TimingStatsLine] = timing_stats.pop("Lines")

            if self.__timing_stats is None:
                self.__timing_stats = timing_stats

            else:
                self.__timing_stats |= timing_stats

            if lines is not None:
                if "Lines" not in self.__timing_stats:
                    self.__timing_stats["Lines"] = lines

                else:
                    for rn, tsl in lines.items():
                        if "PersonalBestLapTime" in tsl:
                            pblt: PersonalBestLapTime = tsl.pop("PersonalBestLapTime")

                        else:
                            pblt = None

                        if "BestSectors" in tsl:
                            b_sectors: Dict[str, BestSector] | List[BestSector] = \
                                tsl.pop("BestSectors")

                        else:
                            b_sectors = None

                        if "BestSpeeds" in tsl:
                            b_speeds: BestSpeeds = tsl.pop("BestSpeeds")

                        else:
                            b_speeds = None

                        self.__timing_stats["Lines"][rn] |= tsl

                        if pblt is not None:
                            if "PersonalBestLapTime" not in self.__timing_stats["Lines"][rn]:
                                self.__timing_stats["Lines"][rn]["PersonalBestLapTime"] = pblt

                            else:
                                self.__timing_stats["Lines"][rn]["PersonalBestLapTime"] |= pblt

                        if b_sectors is not None:
                            if (
                                "BestSectors" in self.__timing_stats["Lines"][rn] and
                                isinstance(b_sectors, Mapping)
                            ):
                                for sn, sd in b_sectors.items():
                                    self.__timing_stats["Lines"][rn]["BestSectors"][int(sn)] |= sd

                            else:
                                self.__timing_stats["Lines"][rn]["BestSectors"] = b_sectors

                        if b_speeds is not None:
                            if "BestSpeeds" not in self.__timing_stats["Lines"][rn]:
                                self.__timing_stats["Lines"][rn]["BestSpeeds"] = b_speeds

                            else:
                                for k, sd in b_speeds.items():
                                    self.__timing_stats["Lines"][rn]["BestSpeeds"][k] |= sd

        elif topic == StreamingTopic.TRACK_STATUS:
            track_status: TrackStatus = update_data
            self.__track_status = track_status

        elif topic == StreamingTopic.WEATHER_DATA:
            weather_data: WeatherData = update_data
            self.__weather_data = weather_data

        else:
            assert False, "Unknown update topic!"

    @property
    def archive_status(self):
        return self.__archive_status

    @property
    def audio_streams(self):
        return self.__audio_streams

    @property
    def car_data(self):
        return self.__car_data

    @property
    def content_streams(self):
        return self.__content_streams

    @property
    def current_tyres(self):
        return self.__current_tyres

    @property
    def driver_list(self):
        return self.__driver_list

    @property
    def extrapolated_clock(self):
        return self.__extrapolated_clock

    @property
    def lap_count(self):
        return self.__lap_count

    @property
    def position(self):
        return self.__position

    @property
    def race_control_messages(self):
        return self.__race_control_messages

    @property
    def session_data(self):
        return self.__session_data

    @property
    def session_info(self):
        return self.__session_info

    @property
    def session_status(self):
        return self.__session_status

    @property
    def team_radio(self):
        return self.__team_radio

    @property
    def timing_app_data(self):
        return self.__timing_app_data

    @property
    def timing_data(self):
        return self.__timing_data

    @property
    def timing_stats(self):
        return self.__timing_stats

    @property
    def track_status(self):
        return self.__track_status

    @property
    def weather_data(self):
        return self.__weather_data


class F1LiveTimingClient:
    def __init__(self, *topics: StreamingTopic, reconnect: bool = True):
        self.__lc = F1LiveClient(*topics, reconnect=reconnect)
        self.__tc = F1TimingClient()

    def __enter__(self):
        self.__lc.__enter__()
        return self

    def __exit__(self, *args):
        self.__lc.__exit__()

    def __iter__(self):
        return self

    def __next__(self):
        while self.__lc.connected:
            _, message = next(self.__lc)

            if "M" in message and len(message["M"]) > 0:
                message_data = message["M"][0]["A"]
                self.__tc.process_update(*message_data)
                return message_data

            if "R" in message:
                self.__tc.process_replay(message["R"])

        raise StopIteration

    @property
    def connected(self):
        return self.__lc.connected

    @property
    def timing_client(self):
        return self.__tc
