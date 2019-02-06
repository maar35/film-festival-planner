using System;
using System.Collections.Generic;
using System.Linq;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Provides a general representation of a screening's attendance and
    /// attendabilty, hiding how these are represented in the screenings file.
    /// </summary>

    public static class ScreeningStatus
    {
        #region Public Members
        public enum Status
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

        #region Private Members
        const string _me = "Maarten";
        static List<string> _myFriends = new List<string> {"Adrienne", "Manfred", "Piggel", "Rijk"};
        static readonly Dictionary<string, Status> _screeningStatusByString;
        static readonly Dictionary<Status, string> _stringByScreeningStatus;
        static Dictionary<Tuple<bool, bool>, TicketsStatus> _ticketStatusByIaTb;
        static readonly Dictionary<string, bool> _stringToBool;
        static readonly Dictionary<bool, string> _boolToString;
        #endregion

        #region Properties
        public const string Me = _me;
        public static List<string> MyFriends => _myFriends;
        public static List<string> FilmFans
        {
            get
            {
                var filmFans = new List<string>(MyFriends);
                filmFans.Insert(0, Me);
                return filmFans;
            }
        }
        public static Dictionary<string, bool> StringToBool => _stringToBool;
        public static Dictionary<bool, string> BoolToString => _boolToString;
        #endregion

        #region Constructors
        static ScreeningStatus()
        {
            _screeningStatusByString = new Dictionary<string, Status> { };
            _screeningStatusByString.Add("ONWAAR", Status.Free);
            _screeningStatusByString.Add("MAARTEN", Status.Attending);
            _screeningStatusByString.Add("FILM", Status.AttendingFilm);
            _screeningStatusByString.Add("TIJD", Status.TimeOverlap);
            _screeningStatusByString.Add("TICKETSNODIG", Status.NeedingTickets);
            _stringByScreeningStatus = _screeningStatusByString.ToDictionary(x => x.Value, x => x.Key);
            _stringByScreeningStatus.Add(Status.AttendedByFriend, "ONWAAR");
            _ticketStatusByIaTb = new Dictionary<Tuple<bool, bool>, TicketsStatus> { };
            _ticketStatusByIaTb[new Tuple<bool, bool>(false, false)] = TicketsStatus.NoTicketsNeeded;
			_ticketStatusByIaTb[new Tuple<bool, bool>(false, true)] = TicketsStatus.MustSellTickets;
            _ticketStatusByIaTb[new Tuple<bool, bool>(true, false)] = TicketsStatus.MustBuyTickets;
			_ticketStatusByIaTb[new Tuple<bool, bool>(true, true)] = TicketsStatus.TicketsArranged;
            _stringToBool = new Dictionary<string, bool> { };
            _stringToBool.Add("ONWAAR", false);
            _stringToBool.Add("WAAR", true);
            _boolToString = _stringToBool.ToDictionary(x => x.Value, x => x.Key);
        }
        #endregion

        #region Public Methods
        static public Status GetScreeningStatus(string statusString, List<string> friendAttendances)
        {
            Status status = _screeningStatusByString[statusString];
            if (status == Status.Free)
            {
                foreach (var friendAttendance in friendAttendances)
                {
                    if (_stringToBool[friendAttendance])
                    {
                        status = Status.AttendedByFriend;
                        break;
                    }
                }
            }
            return status;
        }

        static public string GetScreeningStatusString(Status status)
        {
            return _stringByScreeningStatus[status];
        }

        static public List<string> AttendingFriends(List<string> friendsAttendances)
        {
            return AttendingFilmFans(_myFriends, friendsAttendances);
        }

        static public string Friends()
        {
            string csString = string.Join(",", _myFriends);
            return csString;
        }

        static public string AttendingFriendsString(List<string> attendees)
        {
			var attendingFanStrings = AttendingFilmFansStrings(_myFriends, attendees);
            string csString = string.Join(",", attendingFanStrings);
            return csString;
        }

        public static TicketsStatus GetTicketStatus(bool iAttend, bool ticketsBought)
        {
            return _ticketStatusByIaTb[new Tuple<bool, bool>(iAttend, ticketsBought)];
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
				if (_stringToBool[attendance[i]])
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
                attendeeStrings.Add(_boolToString[attends]);
            }
            return attendeeStrings;
        }
		#endregion
	}
}
