using System;
using System.Collections.Generic;
using System.Linq;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Provides a general representation of a screening's attendance and
    /// attendabilty, hiding how these are represented in the screenings file.
    /// </summary>

    public class ScreeningInfo : ListStreamer
    {
        #region Public Members
        public enum ScreeningStatus
        {
            Free,
            Attending,
            AttendedByFriend,
            AttendingFilm,
            TimeOverlap,
            NoTravelTime,
            NeedingTickets
        }
        public enum Warning
        {
            NoWarning,
            SameMovie,
            TimeOverlap
        }
        public enum TicketsStatus
        {
            NoTicketsNeeded,
            MustBuyTickets,
            MustSellTickets,
            TicketsArranged
        }
        #endregion

        #region Constant Private Members
        private const string _dateTimeFormat = "yyyy-MM-dd HH:mm";
        #endregion

        #region Static Private Members
        private static readonly Dictionary<string, ScreeningStatus> _screeningStatusByString;
        private static readonly Dictionary<ScreeningStatus, string> _stringByScreeningStatus;
        private static readonly Dictionary<Tuple<bool, bool>, TicketsStatus> _ticketStatusByAttendBought;
        #endregion

        #region Properties
        public static string Me => "Maarten";
        public static List<string> FilmFans => new List<string> { Me, "Adrienne", "Manfred", "Piggel", "Rijk" };
        public static List<string> MyFriends => FilmFans.Skip(1).ToList();
        public static Dictionary<string, bool> StringToBool { get; private set; }
        public static Dictionary<bool, string> BoolToString { get; private set; }
        public int FilmId { get; private set; }
        public Screen Screen { get; private set; }
        public DateTime StartTime { get; private set; }
        public string ScreeningTitle { get; set; }
        public List<string> Attendees { get; set; }
        public bool IAttend { get => Attendees.Contains(Me); }
        public List<string> AttendingFriends { get => Attendees.Where(f => f != Me).ToList(); }
        public bool TicketsBought { get; set; }
        public bool SoldOut { get; set; }
        public ScreeningStatus Status { get; set; }
        public bool AutomaticallyPlanned { get; set; } = false;
        #endregion

        #region Constructors
        static ScreeningInfo()
        {
            _screeningStatusByString = new Dictionary<string, ScreeningStatus> { };
            _screeningStatusByString.Add("ONWAAR", ScreeningStatus.Free);
            _screeningStatusByString.Add("MAARTEN", ScreeningStatus.Attending);
            _screeningStatusByString.Add("FILM", ScreeningStatus.AttendingFilm);
            _screeningStatusByString.Add("TIJD", ScreeningStatus.TimeOverlap);
            _screeningStatusByString.Add("REISTIJD", ScreeningStatus.NoTravelTime);
            _screeningStatusByString.Add("TICKETSNODIG", ScreeningStatus.NeedingTickets);
            _stringByScreeningStatus = _screeningStatusByString.ToDictionary(x => x.Value, x => x.Key);
            _stringByScreeningStatus.Add(ScreeningStatus.AttendedByFriend, "ONWAAR");
            _ticketStatusByAttendBought = new Dictionary<Tuple<bool, bool>, TicketsStatus> { };
            _ticketStatusByAttendBought[new Tuple<bool, bool>(false, false)] = TicketsStatus.NoTicketsNeeded;
			_ticketStatusByAttendBought[new Tuple<bool, bool>(false, true)] = TicketsStatus.MustSellTickets;
            _ticketStatusByAttendBought[new Tuple<bool, bool>(true, false)] = TicketsStatus.MustBuyTickets;
			_ticketStatusByAttendBought[new Tuple<bool, bool>(true, true)] = TicketsStatus.TicketsArranged;
            StringToBool = new Dictionary<string, bool> { };
            StringToBool.Add("ONWAAR", false);
            StringToBool.Add("WAAR", true);
            BoolToString = StringToBool.ToDictionary(x => x.Value, x => x.Key);
        }

        public ScreeningInfo() { }

        public ScreeningInfo(string ScreeningInfoText)
        {
            // Parse the fields of the input string.
            string[] fields = ScreeningInfoText.Split(';');
            FilmId = int.Parse(fields[0]);
            string screen = fields[1];
            StartTime = DateTime.Parse(fields[2]);
            ScreeningTitle = fields[3];
            string automaticallyPlanned = fields[4];
            string screeningStatus = fields[5];
            var attendanceStrings = new List<string>(fields[6].Split(','));
            string ticketsBought = fields[7];
            string soldOut = fields[8];

            // Assign members.
            Screen = ScreeningsPlan.Screens.First(s => s.ToString() == screen);
            AutomaticallyPlanned = StringToBool[automaticallyPlanned];
            Attendees = GetAttendeesFromStrings(attendanceStrings);
            TicketsBought = StringToBool[ticketsBought];
            SoldOut = StringToBool[soldOut];
            Status = GetScreeningStatus(screeningStatus, attendanceStrings);
        }

        public ScreeningInfo(int filmId, Screen screen, DateTime startTime)
        {
            FilmId = filmId;
            Screen = screen;
            StartTime = startTime;
            ScreeningTitle = ViewController.GetFilmById(FilmId).Title;
            Attendees = new List<string>{ };
            TicketsBought = false;
            SoldOut = false;
            Status = ScreeningStatus.Free;
        }
        #endregion

        #region Override Methods
        public override bool ListFileIsMandatory()
        {
            return false;
        }

        public override string WriteHeader()
        {
            string headerFmt = "filmid;screen;starttime;screeningtitle;autoplanned;blocked;{0};ticketsbought;soldout";
            return string.Format(headerFmt, FilmFansString());
        }

        public override string Serialize()
        {
            string line = string.Join(
                ';',
                FilmId,
                Screen,
                StartTime.ToString(_dateTimeFormat),
                ScreeningTitle,
                BoolToString[AutomaticallyPlanned],
                _stringByScreeningStatus[Status],
                AttendeesString(),
                BoolToString[TicketsBought],
                BoolToString[SoldOut]
            );
            return line;
        }
        #endregion

        #region Public Methods
        static public ScreeningStatus GetScreeningStatus(string statusString, List<string> friendAttendances)
        {
            ScreeningStatus status = _screeningStatusByString[statusString];
            if (status == ScreeningStatus.Free)
            {
                foreach (var friendAttendance in friendAttendances)
                {
                    if (StringToBool[friendAttendance])
                    {
                        status = ScreeningStatus.AttendedByFriend;
                        break;
                    }
                }
            }
            return status;
        }

        public static string FilmFansString()
        {
            return string.Join(",", FilmFans);
        }

        public static TicketsStatus GetTicketStatus(bool iAttend, bool ticketsBought)
        {
            return _ticketStatusByAttendBought[new Tuple<bool, bool>(iAttend, ticketsBought)];
        }

        public static bool TicketStatusNeedsAttention(Screening screening)
        {
            return screening.IAttend ^ screening.TicketsBought;
        }
        #endregion

        #region Private Methods
        private static List<string> GetAttendeesFromStrings(List<string> attendanceStrings)
		{
			var attendees = new List<string> { };
			int max = new List<int> { FilmFans.Count, attendanceStrings.Count }.Min<int>();
			for (int i = 0; i < max; i++)
			{
				if (StringToBool[attendanceStrings[i]])
				{
					attendees.Add(FilmFans[i]);
				}
			}
			return attendees;
		}

        private string AttendeesString()
        {
            var attendeeStrings = FilmFans.Select(f => BoolToString[Attendees.Contains(f)]);
            return string.Join(',', attendeeStrings);
        }
        #endregion
    }
}
