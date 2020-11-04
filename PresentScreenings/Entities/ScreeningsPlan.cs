using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Represents all screenings of the film festival and is responsible for
    /// adequate access to this information.
    /// </summary>

    public class ScreeningsPlan
    {
        #region Static Properties
        public static List<Screen> Screens { get; private set; }
        public static List<Film> Films { get; private set; }
        public static List<Screening> Screenings { get; private set; }
        public static List<ScreeningInfo> ScreeningInfos { get; private set; }
        public static List<FilmFanFilmRating> FilmFanFilmRatings { get; private set; }
        public static List<FilmInfo> FilmInfos { get; private set; }
        #endregion

        #region Read Only Members
        #endregion

        #region Private Members
        private Dictionary<DateTime, List<Screen>> _dayScreens;
        private int _currDayNumber;
        private int _currScreenNumber;
        private int _currScreenScreeningNumber;
        #endregion

        #region Properties
        public Dictionary<DateTime, Dictionary<Screen, List<Screening>>> ScreenScreenings { get; private set; }
        public Screen CurrScreen => _dayScreens[CurrDay][_currScreenNumber];
        public Screening CurrScreening => ScreenScreenings[CurrDay][CurrScreen][_currScreenScreeningNumber];
        public List<DateTime> FestivalDays { get; private set; }
        public List<Screen> CurrDayScreens => _dayScreens[CurrDay];
        public DateTime CurrDay => FestivalDays[_currDayNumber];
        #endregion

        #region Constructors
        public ScreeningsPlan(string documentsFolder)
        {
            // Initialize file names.
            string screensFile = Path.Combine(documentsFolder, "screens.csv");
            string filmsFile = Path.Combine(documentsFolder, "films.csv");
            string screeningsFile = Path.Combine(documentsFolder, "screenings.csv");
            string screeningInfoFile = Path.Combine(documentsFolder, "screeninginfo.csv");
            string ratingsFile = Path.Combine(documentsFolder, "ratings.csv");
            string filmInfoFile = Path.Combine(documentsFolder, "filminfo.xml");

            // Read screens.
            Screens = new Screen().ReadListFromFile(screensFile, line => new Screen(line));

            // Read film info.
            FilmInfos = FilmInfo.LoadFilmInfoFromXml(filmInfoFile);

            // Read films.
            Films = new Film().ReadListFromFile(filmsFile, line => new Film(line));

            // Read film ratings.
            FilmFanFilmRatings = new FilmFanFilmRating().ReadListFromFile(ratingsFile, line => new FilmFanFilmRating(line));

            // Read screening info.
            ScreeningInfos = new ScreeningInfo().ReadListFromFile(screeningInfoFile, line => new ScreeningInfo(line));

            // Read screenings.
            Screenings = new Screening().ReadListFromFile(screeningsFile, line => new Screening(line));

            InitializeDays();
            _currDayNumber = 0;
            _currScreenNumber = 0;
            _currScreenScreeningNumber = 0;
        }
        #endregion

        #region Private Methods
        private void InitializeDays()
        {
            // Initialize the days, screens and screens per day dictionaries.
            FestivalDays = new List<DateTime> { };
            _dayScreens = new Dictionary<DateTime, List<Screen>> { };
            ScreenScreenings = new Dictionary<DateTime, Dictionary<Screen, List<Screening>>> { };

            // Fill the dictionaries based on on-location screenings.
            var onLocationScreenings = (
                from Screening s in Screenings
                where s.Location
                select s
            ).ToList();
            foreach (Screening screening in onLocationScreenings)
            {
                DateTime day = screening.StartDate;
                if (!FestivalDays.Contains(day))
                {
                    FestivalDays.Add(day);
                    _dayScreens.Add(day, new List<Screen> { });
                    ScreenScreenings.Add(day, new Dictionary<Screen, List<Screening>> { });
                }

                Screen screen = screening.Screen;
                if (!_dayScreens[day].Contains(screen))
                {
                    _dayScreens[day].Add(screen);
                    ScreenScreenings[day].Add(screen, new List<Screening> { });
                }
                ScreenScreenings[day][screen].Add(screening);
            }
            FestivalDays.Sort();
            foreach (var day in FestivalDays)
            {
                _dayScreens[day].Sort();
                foreach (var screen in _dayScreens[day])
                {
                    ScreenScreenings[day][screen].Sort();
                }
            }
        }
        #endregion

        #region Public methods
        public Screening AddOnlineScreening(Screening screening)
        {
            Screen screen = screening.Screen;
            DateTime day = CurrDay;
            Screening tempScreening = new Screening(screening, day);
            _dayScreens[day].Add(screen);
            ScreenScreenings[day].Add(screen, new List<Screening> { });
            ScreenScreenings[day][screen].Add(tempScreening);
            return tempScreening;
        }

        public void RemoveOnlineScreening(Screening oldScreening)
        {
            Screen screen = oldScreening.Screen;
            DateTime day = oldScreening.StartDate;
            ScreenScreenings[day][screen].Remove(oldScreening);
            ScreenScreenings[day].Remove(screen);
            _dayScreens[day].Remove(screen);
        }

        public void SetNextDay(int numberOfDays = 1)
        {
            if (NextDayExists(numberOfDays))
            {
                _currDayNumber += numberOfDays;
                _currScreenNumber = 0;
                _currScreenScreeningNumber = 0;
            }
        }

        public void SetNextScreen(int numberOfScreens = 1)
        {
            if (NextScreenWithinDayExists(numberOfScreens))
            {
                _currScreenNumber += numberOfScreens;
                _currScreenScreeningNumber = 0;
            }
        }

        public void SetNextScreening()
        {
            if (NextScreeningWithinScreenExists(1))
            {
                ++_currScreenScreeningNumber;
            }
            else
            {
                SetNextScreen(1);
            }
        }

        public void SetPrevScreening()
        {
            if (NextScreeningWithinScreenExists(-1))
            {
                --_currScreenScreeningNumber;
            }
            else
            {
                SetNextScreen(-1);
                _currScreenScreeningNumber = ScreenScreenings[CurrDay][CurrScreen].Count - 1;
            }
        }

        public void SetCurrScreening(Screening screening)
        {
            SetNextDay((screening.StartDate - CurrDay).Days);
            _currScreenNumber = CurrDayScreens.IndexOf(screening.Screen);
            var screenScreenings = ScreenScreenings[CurrDay][CurrScreen];
            Screening newCurrScreening = (
                from Screening s in screenScreenings
                where s.FilmId.Equals(screening.FilmId)
                select s
            ).First();
            _currScreenScreeningNumber = screenScreenings.IndexOf(screening);
        }

        public bool NextDayExists(int numberOfDays = 1)
        {
            int nextDayNumber = _currDayNumber + numberOfDays;
            return nextDayNumber >= 0 && nextDayNumber < FestivalDays.Count;
        }

        public bool NextScreenWithinDayExists(int numberOfScreens = 1)
        {
            int nextScreenNumber = _currScreenNumber + numberOfScreens;
            return nextScreenNumber >= 0 && nextScreenNumber < _dayScreens[CurrDay].Count;
        }

        public bool NextScreeningWithinDayExists()
        {
            return NextScreeningWithinScreenExists(1) || NextScreenWithinDayExists(1);
        }

        public bool PrevScreeningWithinDayExists()
        {
            return NextScreeningWithinScreenExists(-1) || NextScreenWithinDayExists(-1);
        }

        public bool NextScreeningWithinScreenExists(int numberOfScreenings = 1)
        {
            int nextScreeningNumber = _currScreenScreeningNumber + numberOfScreenings;
            return nextScreeningNumber >= 0 && nextScreeningNumber < ScreenScreenings[CurrDay][CurrScreen].Count;
        }

        public List<Screening> AttendedScreenings()
        {
            var attendedScreenings = (
                from Screening s in Screenings
                where s.AttendingFilmFans.Count > 0
                orderby s.StartDate
                select s
            ).ToList();
            return attendedScreenings;
        }
        #endregion

        #region Debug methods
        public string DaysAsString()
        {
            string dayString = "";
            string separator = "";
            foreach (var day in FestivalDays)
            {
                dayString = dayString + separator + day.ToShortDateString();
                if (separator.Length == 0)
                {
                    separator = ", ";
                }
            }
            return dayString;
        }

        public string DayScreensAsString()
        {
            string screeningsString = "";
            string separator = "";
            foreach (var screen in _dayScreens[CurrDay])
            {
                screeningsString = screeningsString + separator + screen;
                if (separator.Length == 0)
                {
                    separator = ", ";
                }
            }
            return screeningsString;
        }
        #endregion
    }
}
