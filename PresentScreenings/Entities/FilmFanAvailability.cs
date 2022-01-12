using System;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Film Fan Availability, registers the availability of a film fan for
    /// a period of time during a film festival.
    /// </summary>

    public class FilmFanAvailability : ListStreamer
    {
        #region Contant Private Members
        private const string _dtFormat = "yyyy-MM-dd HH:mm";
        #endregion

        #region Properties
        public string FilmFan { get; }
        public DateTime AvailabilityStart { get; set; }
        public DateTime AvailabilityEnd { get; set; }
        #endregion

        #region Constructors
        public FilmFanAvailability() { }

        public FilmFanAvailability(string filmFanAvailabilityText)
        {
            string[] fields = filmFanAvailabilityText.Split(';');
            FilmFan = fields[0];
            AvailabilityStart = DateTime.Parse(fields[1]);
            AvailabilityEnd = DateTime.Parse(fields[2]);
        }

        public FilmFanAvailability(string filmFan, DateTime availabilityStart, DateTime availabilityEnd)
        {
            FilmFan = filmFan;
            AvailabilityStart = availabilityStart;
            AvailabilityEnd = availabilityEnd;
        }
        #endregion

        #region Override Methods
        public override string ToString()
        {
            return $"{FilmFan} {AvailabilityStart:ddd yyyy-MM-dd HH:mm} - {AvailabilityEnd:ddd yyyy-MM-dd HH:mm}";
        }

        public override bool ListFileIsMandatory()
        {
            return false;
        }

        public override string WriteHeader()
        {
            return "filmfan;starttime;endtime";
        }

        public override string Serialize()
        {
            return string.Join(";", FilmFan, AvailabilityStart.ToString(_dtFormat), AvailabilityEnd.ToString(_dtFormat));
        }
        #endregion

        #region Public Methods
        public bool Equals(string fan, DateTime day)
        {
            return fan == FilmFan && day >= AvailabilityStart && day + new TimeSpan(1, 0, 0, 0) <= AvailabilityEnd;
        }
        #endregion
    }
}
