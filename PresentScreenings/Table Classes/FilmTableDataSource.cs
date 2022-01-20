using System;
using System.Collections.Generic;
using System.Linq;
using AppKit;
using Foundation;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Film table data source, provides data concerning the films displayed
    /// in the film ratings dialog,
    /// </summary>

    public class FilmTableDataSource : NSTableViewDataSource
    {
        #region Private Members
        private static AppDelegate _app;
        private static Dictionary<bool, int> _signByAscending;
        #endregion

        #region Properties
        internal List<Film> Films;
        #endregion

        #region Constructors
        public FilmTableDataSource(AppDelegate app)
        {
            _app = app;
            _signByAscending = new Dictionary<bool, int> { };
            _signByAscending[true] = 1;
            _signByAscending[false] = -1;
        }
        #endregion

        #region Override Methods
        public override nint GetRowCount(NSTableView tableView)
        {
            return Films.Count;
        }

        public override void SortDescriptorsChanged(NSTableView tableView, NSSortDescriptor[] oldDescriptors)
        {
            //base.SortDescriptorsChanged(tableView, oldDescriptors);

            //// Sort the data.
            //if (oldDescriptors.Length > 0)
            //{
            //    // Update sort.
            //    Sort(oldDescriptors[0].Key, oldDescriptors[0].Ascending);
            //}
            //else
            //{
            //    // Grab current descriptors and update sort.
            //    NSSortDescriptor[] sortDescriptor = tableView.SortDescriptors;
            //    Sort(sortDescriptor[0].Key, sortDescriptor[0].Ascending);
            //}

            // Grab current descriptors and update sort.
            NSSortDescriptor sortDescriptor = tableView.SortDescriptors.First(s => true);
            Sort(sortDescriptor.Key, sortDescriptor.Ascending);

            // Refresh table.
            tableView.ReloadData();
        }
        #endregion

        #region Public Methods
        public void Sort(string key, bool ascending)
        {
            var sign = _signByAscending[ascending];

            // Take action based on key.
            switch (key)
            {
                case "Title":
                    Films.Sort((x, y) => sign * x.SequenceNumber.CompareTo(y.SequenceNumber));
                    break;
                case "Duration":
                    Films.Sort((x, y) => sign * x.Duration.CompareTo(y.Duration));
                    break;
                case "Rating":
                    SortByCombinedRating(ScreeningInfo.Me, sign);
                    break;
                default:
                    foreach (var friend in ScreeningInfo.FilmFans)
                    {
                        if (key == friend)
                        {
                            SortByCombinedRating(friend, sign);
                            break;
                        }
                    }
                    break;
            }
        }
        #endregion

        #region Private Methods
        class ratingInfo
        {
            public string Fan;
            public int Rating;
            public ratingInfo(string fan, int rating)
            {
                this.Fan = fan;
                this.Rating = rating;
            }
        }

        private void SortByCombinedRating(string fan, int sign)
        {
            Films.Sort((x, y) => CombinedRating(fan, x, sign).CompareTo(CombinedRating(fan, y, sign)));
        }

        private static int CombinedRating(string fan, Film film, int sign)
        {

            var weightFactor = FilmRating.Values.Count;
            var weightedRating = 0;
            var weight = 1;
            var fans = new List<string>(ScreeningInfo.FilmFans);
            if (fan != ScreeningInfo.Me)
            {
                fans.Remove(fan);
                fans.Insert(0, fan);
            }
            fans.Reverse();
            var filmRatings = fans.Select(f => new ratingInfo(f, GetFilmFanFilmRatingToInt(film, f)));
            foreach (var rating in filmRatings.Select(r => r.Rating))
            {
                weightedRating += weight * rating;
                weight *= weightFactor;
            }
            return sign * weightedRating;
        }

        private static int GetFilmFanFilmRatingToInt(Film film, string fan)
        {
            return int.Parse(ViewController.GetFilmFanFilmRating(film, fan).ToString());
        }
        #endregion
    }
}