using System;
using System.Linq;
using System.Collections.Generic;
using System.Text;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Screenings Planner, plans screenings for "Me" of films that have high
    /// ratings. Screenings must be plannable and will be set as attended by
    /// "Me". The order in which screenings are considered is set as to get an
    /// optimal festival program!
    /// </summary>

    public class ScreeningsPlanner
    {
        #region Private Members
        private List<Screening> _plannedScreenings;
        private ViewController _controller;
        private Action<string> _displayResults;
        private StringBuilder _builder = new StringBuilder();
        private const string _dateTimeFormat = "yyyy-MM-dd HH:mm:ss";
        #endregion

        #region Constructors
        public ScreeningsPlanner(ViewController controller, Action<string> displayResults)
        {
            _controller = controller;
            _displayResults = displayResults;
        }
        #endregion

        #region Public Methods
        public void MakeScreeningsPlan(string filmFan)
        {
            _builder.AppendLine($"{LogTimeString()}  Started planning.");
            _builder.AppendLine();
            _plannedScreenings = new List<Screening> { };
            var rating = FilmRating.MaxRating;
            while (rating.IsGreaterOrEqual(FilmRating.LowestSuperRating))
            {
                // Select films with this rating.
                var films = ScreeningsPlan.Films
                    .Where(f => ViewController.GetMaxRating(f).Equals(rating) && f.FilmScreenings.Count > 0)
                    .ToList();

                // Select free screenings of the selected films.
                var screenings = ScreeningsPlan.Screenings
                    .Where(s => IsPlannable(s, films))
                    .OrderByDescending(s => s.Status == ScreeningInfo.ScreeningStatus.AttendedByFriend)
                    .ThenByDescending(s => s.Status == ScreeningInfo.ScreeningStatus.Free)
                    .ThenBy(s => s.FilmScreeningCount)
                    .ThenBy(s => s is OnDemandScreening)
                    .ThenByDescending(s => s.StartTime)
                    .ToList();

                // Attend the screenings.
                foreach (var screening in screenings)
                {
                    if (screening.IsPlannable)
                    {
                        screening.ToggleFilmFanAttendance(filmFan);
                        screening.AutomaticallyPlanned = true;
                        _controller.UpdateAttendanceStatus(screening);
                        _plannedScreenings.Add(screening);
                    }
                    _controller.ReloadScreeningsView();
                }

                // Display the results of this rating.
                DisplayResultsOfRating(rating, filmFan, films, screenings);

                // Iterate to next lower rating.
                rating.Decrease();
            }

            // Display the sceenings that were planned in this session.
            DisplayPlannedScreenings();

            // Call the display function with the result string.
            _displayResults(_builder.ToString());
        }

        public void UndoScreeningsPlan(string attendee)
        {
            // Display that unplanning is started.
            _builder.AppendLine();
            _builder.AppendLine($"{LogTimeString()}  Started unplanning.");

            // Select the automaticaly planned screenings.
            var screenings = ScreeningsPlan.Screenings.Where(s => s.AutomaticallyPlanned && s.FilmFanAttends(attendee));

            // Unattend the screenings.
            foreach (var screening in screenings)
            {
                screening.ToggleFilmFanAttendance(attendee);
                screening.AutomaticallyPlanned = false;
                _controller.UpdateAttendanceStatus(screening);
            }
            _controller.ReloadScreeningsView();

            // Display that unplanning is done.
            _builder.AppendLine($"{LogTimeString()}  All automatically planned screenings canceled for {attendee}.");
            _builder.AppendLine();

            // Call the display function with the result string.
            _displayResults(_builder.ToString());
        }

        public static string LogTimeString()
        {
            return $"{DateTime.Now.ToString(_dateTimeFormat)}";
        }
        #endregion

        #region Private Methods
        private bool IsPlannable(Screening screening, List<Film> films)
        {
            var inSelectedFilms = films.Any(f => f.FilmId == screening.FilmId);
            return screening.IsPlannable && inSelectedFilms;
        }

        private bool HasAttendedScreening(Film film, string filmFan)
        {
            return film.FilmScreenings.Any(s => s.FilmFanAttends(filmFan));
        }

        private void DisplayResultsOfRating(FilmRating rating, string filmFan, List<Film> films, List<Screening> screenings)
        {
            // Display summary for this rating.
            int highRatedFilmCount = films.Count;
            int plannedFilmCount = films.Where(f => HasAttendedScreening(f, filmFan)).Count();
            _builder.Append($"{LogTimeString()}  {plannedFilmCount} out of {highRatedFilmCount} films with rating {rating} planned for {filmFan}.");

            // Display films with this rating that weren't planned.
            if (highRatedFilmCount - plannedFilmCount > 0)
            {
                _builder.AppendLine();
                _builder.AppendLine($"Films with rating {rating} that could not be planned for {filmFan}:");
                var unplannedFilms = films.Where(f => !HasAttendedScreening(f, filmFan));
                _builder.AppendJoin(Environment.NewLine, unplannedFilms);
            }
            _builder.AppendLine();

            // Display the considered screenings in order.
            _builder.AppendLine();
            if (screenings.Count > 0)
            {
                _builder.AppendLine($"Considered screenings of films rated {rating} in order:");
                _builder.AppendLine();
                _builder.AppendJoin(Environment.NewLine, screenings.Select(s => s.ToConsideredScreeningString()));
                _builder.AppendLine();
            }
            else
            {
                _builder.AppendLine($"No screenings of films rated {rating} could be considered.");
            }
            _builder.AppendLine();
        }

        private void DisplayPlannedScreenings()
        {
            // Display newly planned screenings.
            _builder.AppendLine();
            if (_plannedScreenings.Count > 0)
            {
                _builder.AppendLine($"{LogTimeString()}  {_plannedScreenings.Count} screenings planned:");
                _plannedScreenings.Sort();
                _builder.AppendJoin(Environment.NewLine, _plannedScreenings.Select(s => s.ToPlannedScreeningString()));
            }
            else
            {
                _builder.Append($"{LogTimeString()}  No new screenings planned.");
            }
            _builder.AppendLine();
        }
        #endregion
    }
}
