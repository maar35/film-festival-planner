using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Represents all screenings of the film festival and is responsible for
    /// adequate access to this information.
    /// </summary>

    public class ScreeningsPlan
    {
        #region Private Members
        private Dictionary<DateTime, List<Screen>> _dayScreens;
        private int _currDayNumber;
        private int _currScreenNumber;
        private int _currScreenScreeningNumber;
        private Dictionary<string, Screen> _displayScreenByAbbreviation;
        #endregion

        #region Static Properties
        public static List<FilmFanAvailability> Availabilities { get; private set; }
        public static List<Screen> Screens { get; private set; }
        public static List<Film> Films { get; private set; }
        public static List<Screening> Screenings { get; private set; }
        public static List<ScreeningInfo> ScreeningInfos { get; private set; }
        public static List<FilmFanFilmRating> FilmFanFilmRatings { get; private set; }
        public static List<FilmInfo> FilmInfos { get; private set; }
        public static List<DateTime> FestivalDays { get; private set; }
        #endregion

        #region Properties
        public Dictionary<DateTime, Dictionary<Screen, List<Screening>>> ScreenScreenings { get; private set; }
        public Screen CurrScreen => _dayScreens[CurrDay][_currScreenNumber];
        public Screening CurrScreening => ScreenScreenings[CurrDay][CurrScreen][_currScreenScreeningNumber];
        public List<Screen> CurrDayScreens => _dayScreens[CurrDay];
        public DateTime CurrDay { get => FestivalDays[_currDayNumber]; set => SetDay(value); }
        #endregion

        #region Constructors
        public ScreeningsPlan(string documentsFolder)
        {
            // Read availability.
            Availabilities = new FilmFanAvailability()
                .ReadListFromFile(AppDelegate.AvailabilitiesFile, line => new FilmFanAvailability(line));

            // Read screens.
            Screens = new Screen()
                .ReadListFromFile(AppDelegate.ScreensFile, line => new Screen(line));

            // Read film info.
            FilmInfos = FilmInfo.LoadFilmInfoFromXml(AppDelegate.FilmInfoFile);

            // Read films.
            Films = new Film()
                .ReadListFromFile(AppDelegate.FilmsFile, line => new Film(line));
            Films.Sort();

            // Read film ratings.
            FilmFanFilmRatings = new FilmFanFilmRating()
                .ReadListFromFile(AppDelegate.RatingsFile, line => new FilmFanFilmRating(line));

            // Read screening info.
            ScreeningInfos = new ScreeningInfo()
                .ReadListFromFile(AppDelegate.ScreeningInfoFile, line => new ScreeningInfo(line));

            // Read screenings.
            Screenings = new Screening()
                .ReadListFromFile(AppDelegate.ScreeningsFile, line => PickScreening(line));

            // Filter out screenings that are screened in a combination program.
            SetDisplayedScreenings();

            // Initialize the day schemes.
            InitializeDays();
            _currDayNumber = 0;
            _currScreenNumber = 0;
            _currScreenScreeningNumber = 0;
        }
        #endregion

        #region Public Methods
        public void InitializeDays()
        {
            // Initialize the days, screens and screens per day dictionaries.
            FestivalDays = new List<DateTime> { };
            _dayScreens = new Dictionary<DateTime, List<Screen>> { };
            ScreenScreenings = new Dictionary<DateTime, Dictionary<Screen, List<Screening>>> { };
            InitializeDisplayScreenByAbbreviation();

            // Fill the dictionaries based on the screenings.
            foreach (Screening screening in Screenings)
            {
                // Initialialize on-demand features when applicable.
                InitializeOnLineScreening(screening);

                // Initialize day lists when a new day is encountered.
                DateTime day = screening.StartDate;
                if (!FestivalDays.Contains(day))
                {
                    FestivalDays.Add(day);
                    _dayScreens.Add(day, new List<Screen> { });
                    ScreenScreenings.Add(day, new Dictionary<Screen, List<Screening>> { });
                }

                // Initialize screen lists when a new screen is encountered.
                Screen screen = screening.DisplayScreen;
                if (!_dayScreens[day].Contains(screen))
                {
                    _dayScreens[day].Add(screen);
                    ScreenScreenings[day].Add(screen, new List<Screening> { });
                }
                ScreenScreenings[day][screen].Add(screening);
            }

            // Sort the different lists.
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
            CurrDay = screening.StartDate;
            _currScreenNumber = CurrDayScreens.IndexOf(screening.DisplayScreen);
            var screenScreenings = ScreenScreenings[CurrDay][CurrScreen];
            Screening newCurrScreening = screenScreenings
                .Where(s => s.FilmId == screening.FilmId && s.StartTime == screening.StartTime)
                .First();
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

        #region Private methods
        private Screening PickScreening(string line)
        {
            // Parse the screen from the input line.
            string[] fields = line.Split(';');
            string screenString = fields[Screening.IndexByName["Screen"]];
            Screen screen = Screens
                .Where(s => s.Abbreviation == screenString)
                .First();

            // Return the Screening or subclass, dependant of the screen type.
            return screen.Type == Screen.ScreenType.OnLine ? new OnLineScreening(line)
                : screen.Type == Screen.ScreenType.OnDemand ? new OnDemandScreening(line)
                : new Screening(line);
        }

        private void InitializeDisplayScreenByAbbreviation()
        {
            _displayScreenByAbbreviation = new Dictionary<string, Screen> { };
            var onlineScreens = Screens
                .Where(s => s.Type == Screen.ScreenType.OnLine || s.Type == Screen.ScreenType.OnDemand);
            foreach (var screen in onlineScreens)
            {
                _displayScreenByAbbreviation.Add(screen.Abbreviation, screen);
            }
        }

        private void SetDisplayedScreenings()
        {
            List<Screening> screeningsToRemove = new List<Screening> { };
            foreach (Screening screening in Screenings)
            {
                FilmInfo filmInfo = ViewController.GetFilmInfo(screening.FilmId);
                if (filmInfo.CombinationProgramIds.Count > 0)
                {
                    screeningsToRemove.Add(screening);
                }
            }
            foreach (var screeningToRemove in screeningsToRemove)
            {
                Screenings.Remove(screeningToRemove);
            }
        }

        private void InitializeOnLineScreening(Screening screening)
        {
            if (screening is OnDemandScreening onDemandScreening)
            {
                // Fix IFFR zero length on-demand event.
                int filmId = onDemandScreening.FilmId;
                int screenId = onDemandScreening.Screen.ScreenId;
                string odAbbreviation = onDemandScreening.Screen.Abbreviation;
                List<Screening> localScreenings = Screenings
                    .Where(s => s.FilmId == filmId && s.Screen.ScreenId != screenId)
                    .ToList();
                if (localScreenings.Count > 0)
                {
                    Screening localScreening = localScreenings[0];
                    onDemandScreening.SetEndTime(localScreening);
                }

                // Place film that is available from midnight into day scheme.
                TimeSpan timeOfDay = onDemandScreening.StartTime.TimeOfDay;
                if (timeOfDay < ViewController.EarliestTime)
                {
                    onDemandScreening.MoveStartTime(ViewController.EarliestTime - timeOfDay);
                }
            }
            if (screening is OnLineScreening onLineScreening)
            {
                // Fix overlapping on-line and on-demand screenings on the same "screen".
                FixOverlappingScreenings(onLineScreening);
            }
        }

        private void FixOverlappingScreenings(OnLineScreening onLineScreening)
        {
            // Establish whether there are coinciding screenings.
            var overlappers = Screenings
                .Where(s => s != onLineScreening && s.Overlaps(onLineScreening, true) && (s is OnLineScreening));
            var coinciders = overlappers
                .Where(s => s.Screen == onLineScreening.Screen);
            if (coinciders.Count() == 0)
            {
                onLineScreening.DisplayScreen = onLineScreening.Screen;
                return;
            }

            // Gererate a screen abbreviation different from all overlapping screenings.
            var abbreviations = overlappers
                .Select(s => s.DisplayScreen.Abbreviation)
                .Distinct();
            string abbreviation = onLineScreening.Screen.Abbreviation;
            while (abbreviations.Contains(abbreviation))
            {
                abbreviation = NextAbbreviation(abbreviation);
            }

            // Create a new screen with the new screen abbreviation if none already exists.
            if (!_displayScreenByAbbreviation.ContainsKey(abbreviation))
            {
                _displayScreenByAbbreviation.Add(abbreviation, new Screen(onLineScreening.Screen, abbreviation));
            }

            // Assign the screen with the new screen abbreviation to the Display Screen.
            onLineScreening.DisplayScreen = _displayScreenByAbbreviation[abbreviation];
        }

        private void SetDay(DateTime day)
        {
            var index = FestivalDays.IndexOf(day.Date);
            _currDayNumber = index;
            _currScreenNumber = 0;
            _currScreenScreeningNumber = 0;
        }

        private string NextAbbreviation(string currAbbreviation)
        {
            Match match = Screen.ScreenRegex.Match(currAbbreviation);
            if (match != null)
            {
                string root = match.Groups[1].Value;
                int version = currAbbreviation == root ? 1 : int.Parse(match.Groups[2].Value);
                return $"{root}{version + 1}";
            }
            return string.Empty;
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
