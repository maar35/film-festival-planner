using System;
using System.Collections.Generic;
using System.Linq;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Provides a general representation of a screening's attendance and
    /// attendabilty, hiding how these are represented in the screenings file.
    /// </summary>

    public class ScreeningInfo : ListReader<ScreeningInfo>, ICanWriteList
    {
        #region Public Members
        public enum ScreeningStatus
        {
            Free,
            Attending,
            AttendedByFriend,
            AttendingFilm,
            TimeOverlap,
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
        public List<string> AttendingFilmFans { get; set; }
        public bool IAttend { get => AttendingFilmFans.Contains(Me); }
        public List<string> AttendingFriends { get => AttendingFilmFans.Where(f => f != Me).ToList(); }
        public bool TicketsBought { get; set; }
        public bool SoldOut { get; set; }
        public ScreeningStatus Status { get; set; }
        #endregion

        #region Constructors
        static ScreeningInfo()
        {
            _screeningStatusByString = new Dictionary<string, ScreeningStatus> { };
            _screeningStatusByString.Add("ONWAAR", ScreeningStatus.Free);
            _screeningStatusByString.Add("MAARTEN", ScreeningStatus.Attending);
            _screeningStatusByString.Add("FILM", ScreeningStatus.AttendingFilm);
            _screeningStatusByString.Add("TIJD", ScreeningStatus.TimeOverlap);
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
            string screeningStatus = fields[4];
            string myAttendanceString = fields[5];
            var myFriendsAttendanceStrings = new List<string>(fields[6].Split(','));
            string ticketsBought = fields[7];
            string soldOut = fields[8];

            // Assign members.
            Screen = (from Screen s in ScreeningsPlan.Screens where s.ToString() == screen select s).ElementAt(0);
            AttendingFilmFans = GetAttendingFilmFans(myAttendanceString, myFriendsAttendanceStrings);
            TicketsBought = StringToBool[ticketsBought];
            SoldOut = StringToBool[soldOut];
            Status = GetScreeningStatus(screeningStatus, myFriendsAttendanceStrings);
        }

        public ScreeningInfo(int filmId, Screen screen, DateTime startTime)
        {
            FilmId = filmId;
            Screen = screen;
            StartTime = startTime;
            ScreeningTitle = ViewController.GetFilmById(FilmId).Title;
            AttendingFilmFans = new List<string>{ };
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
        #endregion

        #region Interface Implemantations
        string ICanWriteList.Serialize()
        {
            string line = string.Join(
                ';',
                FilmId,
                Screen,
                StartTime.ToString(_dateTimeFormat),
                ScreeningTitle,
                GetScreeningStatusString(Status),
                BoolToString[IAttend],
                AttendingFriendsString(AttendingFriends),
                BoolToString[TicketsBought],
                BoolToString[SoldOut]
            );
            return line;
        }
        #endregion

        #region Public Methods
        public static string WriteHeader()
        {
            string headerFmt = "filmid;screen;starttime;screeningtitle;blocked;maarten;{0};ticketsbought;soldout";
            return string.Format(headerFmt, FriendsString());
        }

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

        static public string GetScreeningStatusString(ScreeningStatus status)
        {
            return _stringByScreeningStatus[status];
        }

        static public string FriendsString()
        {
            return string.Join(",", MyFriends);
        }

        public static string AttendingFriendsString(List<string> attendees)
        {
			var attendingFanStrings = AttendingFilmFansStrings(MyFriends, attendees);
            string csString = string.Join(",", attendingFanStrings);
            return csString;
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
        private static List<string> GetAttendingFilmFans(string myAttendanceString, List<string> myFriendAttendanceStrings)
        {
            var attendanceStrings = new List<string> { myAttendanceString };
            attendanceStrings.AddRange(myFriendAttendanceStrings);
            return GetAttendingFilmFans(FilmFans, attendanceStrings);
        }

        private static List<string> GetAttendingFilmFans(List<string> fans, List<string> attendanceStrings)
		{
			var attendees = new List<string> { };
			int max = new List<int> { fans.Count, attendanceStrings.Count }.Min<int>();
			for (int i = 0; i < max; i++)
			{
				if (StringToBool[attendanceStrings[i]])
				{
					attendees.Add(fans[i]);
				}
			}
			return attendees;
		}

        private static List<string> AttendingFilmFansStrings(List<string> fans, List<string> attendees)
        {
            var attendeeStrings = new List<string> { };
            foreach (var fan in fans)
            {
                bool attends = attendees.Contains(fan);
                attendeeStrings.Add(BoolToString[attends]);
            }
            return attendeeStrings;
        }
        #endregion
    }
}
