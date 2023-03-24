using System;
using System.Collections.Generic;

namespace PresentScreenings.TableView
{
    public class Theater : ListStreamer
    {
        #region Public Members
        public enum PriorityValue
        {
            NoGo,
            Low,
            High,
        }
        #endregion

        #region Properties
        public int TheaterId { get; }
        public string City { get; }
        public string Name { get; }
        public string Abbreviation { get; }
        public PriorityValue Priority { get; private set; }
        #endregion

        #region Constructors
        // Constructor to read records from the interface file.
        public Theater(string theaterText)
        {
            // Assign the fields of the input string.
            string[] fields = theaterText.Split(';');
            string theaterId = fields[0];
            City = fields[1];
            Name = fields[2];
            Abbreviation = fields[3];

            // Assign properties that need calculating.
            TheaterId = int.Parse(theaterId);

            // EXPRIMENT introduce priority.
            List<int> eligibleTheaters = new List<int> { 1, 15 };
            if (eligibleTheaters.Contains(TheaterId))
            {
                Priority = PriorityValue.High;
            }
            else
            {
                Priority = PriorityValue.Low;
            }
        }

        // Empty constructor to facilitate ListStreamer method calls.
        public Theater() { }
        #endregion

        #region Override Methods
        public override bool ListFileHasHeader()
        {
            return false;
        }

        public override string ToString()
        {
            return $"{Name} {City}";
        }
        #endregion
    }
}
