using System;
using System.Collections.Generic;
using System.Linq;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Provides a general representation of a screening's attendance and
    /// attendabilty, hiding how these are represented in the screenings file.
    /// </summary>

    public class ScreeningInfo : ICanWriteList
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
        private const string _timeFormat = "HH:mm";
        private const string _me = "Maarten";
        #endregion

        #region Static Private Members
        private static readonly Dictionary<string, ScreeningStatus> _screeningStatusByString;
        private static readonly Dictionary<ScreeningStatus, string> _stringByScreeningStatus;
        private static readonly Dictionary<Tuple<bool, bool>, TicketsStatus> _ticketStatusByAttendBought;
        #endregion

        #region Properties
        public const string Me = _me;
        public static List<string> MyFriends { get; } = new List<string> { "Adrienne", "Manfred", "Piggel", "Rijk" };
        public static List<string> FilmFans
        {
            get
            {
                var filmFans = new List<string>(MyFriends);
                filmFans.Insert(0, Me);
                return filmFans;
            }
        }
        public static Dictionary<string, bool> StringToBool { get; private set; }
        public static Dictionary<bool, string> BoolToString { get; private set; }
        public int FilmId { get; private set; }
        public Screen Screen { get; private set; }
        public DateTime StartTime { get; private set; }
        public string ScreeningTitle { get; set; }
        public bool IAttend { get; set; }
        public List<string> AttendingFriends { get; set; }
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

        public ScreeningInfo(string ScreeningInfoText)
        {
            // Parse the fields of the input string.
            string[] fields = ScreeningInfoText.Split(';');
            FilmId = int.Parse(fields[0]);
            string screen = fields[1];
            StartTime = DateTime.Parse(fields[2]);
            ScreeningTitle = fields[3];
            string screeningStatus = fields[4];
            string myAttendance = fields[5];
            var myFriendsAttendances = new List<string>(fields[6].Split(','));
            string ticketsBought = fields[7];
            string soldOut = fields[8];

            // Assign members.
            Screen = (from Screen s in ScreeningsPlan.Screens where s.ToString() == screen select s).ElementAt(0);
            IAttend = StringToBool[myAttendance];
            AttendingFriends = GetAttendingFriends(myFriendsAttendances);
            TicketsBought = StringToBool[ticketsBought];
            SoldOut = StringToBool[soldOut];
            Status = GetScreeningStatus(screeningStatus, myFriendsAttendances);
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
            return string.Format(headerFmt, ScreeningInfo.Friends());
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

        static public List<string> GetAttendingFriends(List<string> friendsAttendances)
        {
            return AttendingFilmFans(MyFriends, friendsAttendances);
        }

        static public string Friends()
        {
            string csString = string.Join(",", MyFriends);
            return csString;
        }

        static public string AttendingFriendsString(List<string> attendees)
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
		static List<string> AttendingFilmFans(List<string> fans, List<string> attendance)
		{
			var attendees = new List<string> { };
			int max = new List<int> { fans.Count, attendance.Count }.Min<int>();
			for (int i = 0; i < max; i++)
			{
				if (StringToBool[attendance[i]])
				{
					attendees.Add(fans[i]);
				}
			}
			return attendees;
		}

        static List<string> AttendingFilmFansStrings(List<string> fans, List<string> attendees)
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
