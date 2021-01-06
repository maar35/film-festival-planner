using System;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Film Fan Availability, registers the availability of a film fan for
    /// a period of time during a film festival.
    /// </summary>

    public class FilmFanAvailability : ListStreamer
    {
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
            return string.Join(";", FilmFan, AvailabilityStart.ToString(), AvailabilityEnd.ToString());
        }
        #endregion
    }
}
