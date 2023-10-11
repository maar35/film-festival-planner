using System;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Class City is a simple representation of a city, wich is used in
    /// theaters and festivals.
    /// </summary>

    public class City : ListStreamer
    {
        #region Properties
        public int CityId { get; }
        public string Name { get; }
        public string Country { get; }
        #endregion

        #region Constructors
        public City() { }

        public City(string cityLine)
        {
            // Assign the fields of the input string.
            string[] fields = cityLine.Split(";");
            string cityId = fields[0];
            Name = fields[1];
            Country = fields[2];

            // Assign properties that need calculating.
            CityId = int.Parse(cityId);
        }
        #endregion

        #region Override Methods
        public override bool ListFileHasHeader()
        {
            return false;
        }

        public override bool ListFileIsMandatory()
        {
            return true;
        }

        public override string ToString()
        {
            return Name;
        }
        #endregion
    }
}
