import React, { Fragment, Component, useState } from 'react';
import './App.css';
import Col from 'react-bootstrap/Col';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Button from 'react-bootstrap/Button';
import Image from 'react-bootstrap/Image';
import Alert from 'react-bootstrap/Alert';
import Table from 'react-bootstrap/Table';
import Dropdown from 'react-bootstrap/Dropdown';
import DropdownButton from 'react-bootstrap/DropdownButton';
import Modal from 'react-bootstrap/Modal';
import 'bootstrap/dist/css/bootstrap.css';
import DatePicker from 'react-datepicker';
import "react-datepicker/dist/react-datepicker.css";
import {FaCaretLeft, FaCaretRight, FaHeart, FaFileExcel, FaRegCalendarAlt, FaCommentDots, FaRegCommentDots, FaDownload, FaPassport, FaInfo, FaChartLine, FaSignOutAlt, FaList} from 'react-icons/fa';

import SelectSearch from 'react-select-search';
import "./select-search.css";

import { Histogram, DensitySeries, BarSeries, withParentSize, XAxis, YAxis } from '@data-ui/histogram';

import { Slider, Rail, Handles, Tracks, Ticks } from 'react-compound-slider'
import { SliderRail, Handle, Track, Tick } from './components.js'

import { timeFormat, timeParse } from "d3-time-format";

import {
  Map,
  Rectangle,
  TileLayer,
  Tooltip,
  ImageOverlay,
  LayersControl,
  Popup,
  FeatureGroup,
  Circle,
  withLeaflet,
  GeoJSON,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from 'leaflet';
import { ReactLeafletSearch } from 'react-leaflet-search'

import HeatmapOverlay from 'leaflet-heatmap'

import CookieConsent from "react-cookie-consent";

const ZERO_DATA_DAY_HEIGHT = 0.25;
const acquisition_datetime_formatter = timeFormat("%Y-%m-%d");
const human_datetime_formatter = timeFormat("%d-%b-%Y");
const yearless_human_datetime_formatter = timeFormat("%d-%b");
const parseDate = timeParse("%Y-%m-%d");
const HEATMAP_MAX = 0.2e-3

const ResponsiveHistogram = withParentSize(({ parentWidth, parentHeight, ...rest}) => (
  <Histogram
    width={parentWidth}
    height={parentHeight}
    {...rest}
  />
));

const IS_DEV = (!process.env.NODE_ENV || process.env.NODE_ENV === 'development');
const API_ADDRESS = IS_DEV?"http://127.0.0.1:8080/data":"http://127.0.0.1:8080/data"


const HIST_COLORS = {2019:'#5B5085D0', 2020:'#EA5959D0'}
const DIFF_COLORS = {2019:'#3B3083D0', 2020:'#CA3939D0'}
const sliderStyle = {
  position: 'relative',
  width: '100%',
  padding:15,

}

function getDateFromDatum(datum){
 return parseDate(datum.date_str)
}

function datesEqual(a, b) {
  if (a == null || b == null) return false;
  return a.getTime() === b.getTime();
}

function arraysEqual(a, b) {
  if (a === b) return true;
  if (a == null || b == null) return false;
  if (a.length !== b.length) return false;

  // If you don't care about the order of the elements inside
  // the array, you should sort both arrays here.
  // Please note that calling sort on an array will modify that array.
  // you might want to clone your array first.

  for (var i = 0; i < a.length; ++i) {
    // console.log("|"+a[i]+"=="+b[i]+"|")
    if (a[i] !== b[i]) return false;
  }
  return true;
}

function fixCase(str) {
  let woutPars = str.split('(')[0]
  let words = woutPars.split(' ')
  let reconstructed = ''
  for(let i=0; i<words.length; i++)
  {
    if(words[i] === ""){
      continue;
    }
    let eachWord = words[i].toLowerCase()
    reconstructed = reconstructed + eachWord[0].toUpperCase() + eachWord.substring(1).toLowerCase() 
    reconstructed = reconstructed + ' '
  }
  reconstructed = reconstructed[reconstructed.length-1]===' ' ? reconstructed.substring(0, reconstructed.length-1) : reconstructed
  return reconstructed;
}

function safeCopyDate(date){
  if(date){
    let ret_val = new Date(date.getTime())
    Object.keys(date).forEach( key => {ret_val[key]=date[key]} )
    // if(date.index)
    //   ret_val.index = date.index
    // if(date.product_type)
    //   ret_val.product_type = date.product_type
    // console.log('copied', ret_val.index)
    return ret_val
  }
}

function modifyDatumYear(datum){
    let newBin0 = new Date(datum.bin0)
    let newBin1 = new Date(datum.bin1)
    if (parseDate(datum.date_str).getFullYear()===2020){
      newBin0.setFullYear(newBin0.getFullYear()-1)
      newBin1.setFullYear(newBin1.getFullYear()-1)
    }
    else{
      // console.log('uh oh', newBin0, newBin1)
    }
    datum.bin0 = newBin0.getTime()
    datum.bin1 = newBin1.getTime()
}

function isDatumInsideSliderRange(datum, sliderStart, sliderEnd){
  const bin0 = new Date(datum.bin0)
  const bin1 = new Date(datum.bin1)
  if(bin0.getFullYear()==bin1.getFullYear()){
    const isEarlier = bin0.getMonth()<sliderStart.getMonth() || (bin0.getMonth()===sliderStart.getMonth() && bin0.getDate()<sliderStart.getDate())
    const isLater = bin1.getMonth()>sliderEnd.getMonth() || (bin1.getMonth()===sliderEnd.getMonth() && bin1.getDate()>sliderEnd.getDate())
    const isOutside = isEarlier || isLater
    return !isOutside
  }
  else if(bin0.getFullYear()===2019){ // we need to compare years somehow OR use stricter outside rules to get away easy?
    const isBin0Earlier = bin0.getMonth() < sliderStart.getMonth() || (bin0.getMonth()===sliderStart.getMonth() && bin0.getDate()<=sliderStart.getDate())
    const isBin0Later = bin0.getMonth() > sliderEnd.getMonth() || (bin0.getMonth()===sliderEnd.getMonth() && bin0.getDate()>=sliderEnd.getDate())
    const isBin0Outside = isBin0Earlier || isBin0Later
    return !isBin0Outside
  }
  else if(bin1.getFullYear()===2019){ // we need to compare years somehow OR use stricter outside rules to get away easy?
    const isBin1Earlier = bin1.getMonth() < sliderStart.getMonth() || (bin1.getMonth()===sliderStart.getMonth() && bin1.getDate()<=sliderStart.getDate())
    const isBin1Later = bin1.getMonth() > sliderEnd.getMonth() || (bin1.getMonth()===sliderEnd.getMonth() && bin1.getDate()>=sliderEnd.getDate())
    const isBin1Outside = isBin1Earlier || isBin1Later
    return !isBin1Outside
  }
}

function scaleBinnedData(binned_data, scaler){

  return binned_data.map( datum => {
    let date = getDateFromDatum(datum);
    let bin0 = new Date(date)
    bin0.setDate(bin0.getDate()-scaler/8)
    bin0.setHours(0)
    bin0.setMinutes(0+Math.random()*59)
    bin0.setSeconds(1+Math.random()*59)
    let bin1 = new Date(date)
    bin1.setDate(bin1.getDate()+scaler/8)
    bin1.setHours(23)
    bin1.setMinutes(59-Math.random()*59)
    bin1.setSeconds(58-Math.random()*59)
    return {bin0: bin0.getTime(), 
            bin1:bin1.getTime(), 
            count: datum.count, 
            id: datum.id,
            date_str: datum.date_str,
            product_type: datum.product_type,
            city: datum.city,
          };
  })
}

function avg_mode_extension(averaging_mode) {
  if(averaging_mode === 'Raw'){
    return ''
  }
  else if(averaging_mode === 'Interpolated'){
    return '_interpd'
  }
  else if(averaging_mode === 'Averaged'){
    return '_avg10'
  }
  return ''
}

function ModalDismissible() {
  const [show, setShow] = useState(false);

  const handleClose = () => setShow(false);

  return (
   		<Fragment>

      <Modal show={show} onHide={handleClose}>
        <Modal.Header closeButton>
          <Modal.Title>Hello! <FaInfo /></Modal.Title>
        </Modal.Header>
        <Modal.Body>          
        	Mind you <FaHeart />, this is a live development demo product! You may encounter bugs. Please let us know at info[at]novit[dot]ai if you do so.
		</Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={handleClose}>
            Close
          </Button>
          <Button variant="primary" onClick={handleClose}>
            Thank you!
          </Button>
        </Modal.Footer>
      </Modal>
   		</Fragment>

  );
}

function AlertDismissible() {
  const [show, setShow] = useState(false);

  return (
      <Alert show={show} variant="warning" style={{margin:20}}>
        <Alert.Heading>Hello</Alert.Heading>
        <p>
          Mind you <FaHeart />, this is a live development demo product! You may encounter bugs. Please let us know at info[at]novit[dot]ai if you do so.
        </p>
        <hr />
        <div className="d-flex justify-content-end">
          <Button onClick={() => setShow(false)} variant="outline-warning">
            Thanks!
          </Button>
        </div>
      </Alert>
  );
}

function colormap_to_gradient(map_name) {
  let map = COLORMAPS[map_name]
  let arr = ['0deg']
  Object.keys(map).map(val => arr.push(map[val] + ' ' + val*100 + '%'))
  return 'linear-gradient(' + arr.toString() + ')'
}

const sleep = (milliseconds) => {
  return new Promise(resolve => setTimeout(resolve, milliseconds))
}

const implementedEmissionTypes = ['NO2']
const implementedAveragingModes = ['Raw', 'Interpolated', 'Averaged']
const UNITS = {CO:'mol/m\u00B2', NO2:'mol/m\u00B2', CH4:'1e-9'}
const RADIUS = {Raw:{CO: 0.04, NO2: 0.04,}, Interpolated:{CO: 0.02, NO2: 0.04,}, Averaged:{CO: 0.02, NO2: 0.04,}}
const dataSummaryTypes = ['min', 'max', 'mean']
const MIN_PORT_CHANGE_ZOOM = 4
const initial_area = 'milan' 
const initial_latlon = [45.47554027158593, 9.766845703125002]
const COLORMAPS = {
                    hot:{ '0.0':'black',
                        '0.35':'red',
                        '0.5':'orange',
                        '0.75':'yellow',
                        '1.0':'white',
                        },
                  inferno:{ '0.0':'black',
                        '0.25':'navy',
                        '0.4':'purple',
                        '0.5':'red',
                        '0.65':'orange',
                        '0.85':'yellow',
                        '1.0':'white',
                        },
                  magma:{ '0.0':'black',
                        '0.25':'navy',
                        '0.4':'purple',
                        '0.5':'magenta',
                        '0.65':'pink',
                        '1.0':'white',
                        },
                  }

class App extends Component {

  constructor(props, context) {
    super(props, context);
    this.map_ref = React.createRef()
    this.cities = []
    this.state = {
      keyboard_shortcuts_enabled: true,
      basic_mode: 2,
      width: 0,
      height: 0,
      result: "",
      colormap: 'inferno',
      areas: [initial_area],
      product_type: 'NO2',
      selectedDay: new Date(),
      selectedDayIndex: undefined,
      summary_type: 'mean',
      averaging_mode: 'Averaged', // Raw, Interpolated
      geodata: {},
      all_data : undefined,
      histogram_data : undefined,
      summary_loaded: false,
      domain: [new Date(2019, 0, 1).getTime(), new Date(2019, 11, 31, 23, 59, 59).getTime()],
      show_dense: true,
      values: [new Date(2019, 0, 1).getTime(), new Date(2019, 11, 31, 23, 59, 59).getTime()],
      zoom: 6,
      centerLat: initial_latlon[0],
      centerLon: initial_latlon[1],
      availablePorts: [],
      clickPos: {lat: 41.03793, lng: 29.06708},
      histogram_scaler: 0,
      wait: true,
      error: undefined,
      product_description: '',
    };
  }

  componentDidMount() {
    // console.log('componentDidMount')
    this.updateWindowDimensions();
    window.addEventListener('resize', this.updateWindowDimensions);

    if(!this.state.summary_loaded){
        this.getCities()
      	this.getSummary()
    }

    // Auth.currentAuthenticatedUser({
    //     bypassCache: false  // Optional, By default is false. If set to true, this call will send a request to Cognito to get the latest user data
    // }).then(user => s('CognitoUser',user))
    // .catch(err => console.log(err));


    // console.log("authState",this.props.authState)

    // Auth.currentSession()
    //     .then(data => console.log('CognitoUserSession',data))
    //     .catch(err => console.log(err));

    document.addEventListener('keyup', this.appKeyUpHandler);
    // console.log(data)
    // console.log(geodata)
    // console.log(testData)
  }
  
  componentWillUnmount() {
    window.removeEventListener('resize', this.updateWindowDimensions);
    document.removeEventListener('keyup', this.appKeyUpHandler);  
  }

  // componentWillUpdate() {
  //     this.getSummary()
  // }

  updateWindowDimensions = () => {
    this.setState({ width: window.innerWidth, height: window.innerHeight });
  }

  set_cursor_waititing = ( is_waiting) =>
  {
      // console.log(this.map_ref)
      this.setState({wait: is_waiting})
      if(!this.map_ref.current)
        return
      if(!this.map_ref.current.leafletElement)
        return
      if(this.map_ref.current.leafletElement._container) {
        if(is_waiting){
            this.map_ref.current.leafletElement._container.style.cursor = 'wait'
        }
        else{
            this.map_ref.current.leafletElement._container.style.cursor = ''
        }
      }

  }

  zoom_to_cover_ports = (port_ids) => {
    let all_corners = []
    this.state.areas.map( (key, index) => {
      const bound0 = L.latLng(this.cities[key][0])
      const bound1 = L.latLng(this.cities[key][1])
      all_corners.push(bound0);
      all_corners.push(bound1);
    }); 
    this.map_ref.current.leafletElement.flyToBounds(L.latLngBounds(all_corners).pad(-0.10))
    this.bar_clicked = false
  }

  getCities = async () => {
    const handleJsonResponse = response => {
      // console.log('cities as response', response)
      this.cities = {}
      Object.keys(response).forEach( (city, index) => { 
          let lat1lat2lon1lon2 = response[city]
          let corner1 = L.latLng(lat1lat2lon1lon2[0], lat1lat2lon1lon2[2])
          let corner2 = L.latLng(lat1lat2lon1lon2[1], lat1lat2lon1lon2[3])
          this.cities[city] = L.latLngBounds(corner1, corner2)
        })
      // console.log('cities', this.cities)
      // this.setState({centerLat: (response[initial_area]['0'] + response[initial_area]['1'])/2,
                    // centerLon: (response[initial_area]['2'] + response[initial_area]['3'])/2,
                    // clickPos: {lat:(response[initial_area]['0'] + response[initial_area]['1'])/2, lon:(response[initial_area]['2'] + response[initial_area]['3'])/2}})

      let potential_alternative_init_cities = window.location.pathname.substr(1).split(',')
      potential_alternative_init_cities = potential_alternative_init_cities.filter( potential_city => Object.keys(this.cities).includes(potential_city) )
      let citybounds_collection = potential_alternative_init_cities.map( cityname => this.cities[cityname] )
      if ( citybounds_collection.length >= 1 ){
        let overall_bounds = L.latLngBounds(citybounds_collection[0].getSouthWest(), citybounds_collection[0].getNorthEast())
        citybounds_collection.forEach( city_bounds => overall_bounds.extend(city_bounds) )
        let map_bounds = this.map_ref.current.leafletElement.getBounds()
        if(map_bounds.contains(overall_bounds))
        {
          console.log('map already zoomed out enough')
          // this.query_acquisition(this.state.selectedDay, this.state.product_type)
        }
        else
        {
          console.log('nope we need to fly away')
        }
        this.map_ref.current.leafletElement.flyToBounds(overall_bounds)
      }
      else{
        window.history.pushState( this.state.areas, 'SkyBase '+initial_area, '/'+initial_area )
        this.map_ref.current.leafletElement.flyToBounds(this.cities[initial_area])
      }
    }
    fetch(API_ADDRESS + '/' + 'cities.json', 
    {
      headers: {
        'Accept': 'application/json',
        //'Content-Type': 'application/json',
      },
      method: 'GET',
    })
    .then((response) =>{
      if (response.status !== 200) {
        this.setState({error:response.status})
        console.log("non 200 OK response in getCities()->fetch()", response)
      }
      else {
        return response;
      } 
    })
    .then(response => response.json())
    .then(handleJsonResponse)
  }

  getSummary = async (min_areas) => {
    const handleJsonResponse = response => {
      let city = response.city
      // console.log('handling summary response for', min_areas, response)
      var data = {}
      var selectedDay = new Date(1990, -1+1, 3)
      for (var j=0; j<Object.keys(response).length; j++){
        let product_type = Object.keys(response)[j]
        if(!implementedEmissionTypes.includes(product_type)){
          continue
        }
        data[product_type] = []
        let result = response[product_type]
        let sorted_keys = Object.keys(result)
        sorted_keys.sort( (a,b) => parseDate(a).getTime() - parseDate(b).getTime() )
        for (var i = 0; i < sorted_keys.length; i++) {
          let datum_date = sorted_keys[i];
          let datum_count = result[datum_date][this.state.summary_type]*1e3;
          let datum_date_dt = parseDate(datum_date)
          // console.log('datum_date_dt', datum_date_dt)
          let bin0 = new Date(datum_date_dt)
          bin0.setDate(bin0.getDate())
          // bin0.setHours(0)
          // bin0.setMinutes(0)
          let bin1 = new Date(datum_date_dt)
          bin1.setDate(bin1.getDate())
          // bin1.setHours(23)
          // bin1.setMinutes(59)
          data[product_type][i] = { bin0: bin0.getTime(), 
                          bin1: bin1.getTime(), 
                          count: datum_count,
                          date_str: datum_date, 
                          id: city+'|'+product_type+'|'+datum_date, 
                          product_type: product_type,
                          city: city,
                    }
        }
        data[product_type] = scaleBinnedData(data[product_type], 0)
      }
      // console.log('returning city data', data)
      return data
    }
    const mergeJsonResponses = city_summaries => {
      // console.log('merging summary response for', city_summaries)
      // console.log('city_summaries', city_summaries)
      let all_data = {}
      implementedEmissionTypes.forEach( product_type => {
        all_data[product_type] = {}
        city_summaries.forEach( city_data => {
          if(!city_data){
            // console.log('citydata is empty', city_summaries)
            return
          }
          let dataarray = city_data[product_type]
          if(dataarray === undefined) {
            // console.log('citydata is empty for product_type', product_type, city_data)
            return
          }
          dataarray.forEach( (datum,index) => {
            if(all_data[product_type][datum.date_str]){
              all_data[product_type][datum.date_str].count += datum.count
              const existing_cities = all_data[product_type][datum.date_str].city.split(',')
              let new_datum_cities = [...existing_cities]
              new_datum_cities.push(datum.city)
              new_datum_cities.sort()
              all_data[product_type][datum.date_str].city = new_datum_cities.join(',')
              all_data[product_type][datum.date_str].id = new_datum_cities+'|'+product_type+'|'+datum.date_str 
            }
            else{
              all_data[product_type][datum.date_str] = {...datum}
            }
          })
        })
      })

      const areas_str = this.state.areas.sort().join(',')
      // console.log('filtering data without city string as ', areas_str)
      // console.log('all_data pre filtering', JSON.stringify(all_data))
      implementedEmissionTypes.forEach( product_type => {
          if(all_data[product_type] === undefined){
            return
          }
          Object.keys(all_data[product_type]).forEach(date_str => {
            //console.log(all_data[product_type][date_str])
            if(all_data[product_type][date_str].city !== areas_str){
              // console.log('deleting datum because', all_data[product_type][date_str].city)
              delete all_data[product_type][date_str]
            }
          })
        }
      )
      // console.log('all_data post filtering', JSON.stringify(all_data))
      let data = {}
      var dates = []
      var selectedDay = new Date(1990, -1+1, 3)
      implementedEmissionTypes.forEach( product_type => {
        data[product_type] = []
        dates[product_type] = []
        let sorted_keys = Object.keys(all_data[product_type])
        sorted_keys.sort( (a,b) => parseDate(a).getTime() - parseDate(b).getTime() )
        sorted_keys.forEach( (date_str, index) => {
          let datum_date = date_str;
          let datum_date_dt = parseDate(datum_date)
          datum_date_dt.product_type = product_type
          datum_date_dt.index = index
          if (datum_date_dt > selectedDay){
            selectedDay = safeCopyDate(datum_date_dt)
          }
          // if(!dates.some( existing_date => datesEqual(existing_date, datum_date_dt)))
          dates[product_type].push(datum_date_dt)
          data[product_type].push( all_data[product_type][date_str] )
        })
      })  
      // console.log('all_data after summary', data)
      // console.log('all_dates after summary', dates)
      Object.keys(dates).map( product_type => dates[product_type].sort( (a,b) => a.getTime() - b.getTime() ) )
      let mindates = Object.keys(dates).map( product_type => Math.min.apply(null, dates[product_type]) )
      let maxdates = Object.keys(dates).map( product_type => Math.max.apply(null, dates[product_type]) )
      let domain  = [Math.min.apply(null, mindates), Math.max.apply(null, maxdates)]
      // console.log('min/max dates: ',domain)
      this.setState({
                    measurement_dates: dates, 
                    histogram_data: data,
                    all_data: data, 
                    // domain: domain, 
                    // values:[Math.min.apply(null,dates) ,Math.max.apply(null,dates)],
                  })
      if(!this.state.summary_loaded){
        console.log('first time summary loaded')
        this.setState({summary_loaded: true })
        this.handleDayChange(selectedDay)
        // this.findAndUpdateSelectedDayIndex(selectedDay)
        this.on2020Click();

        // let area_bounds = this.cities[initial_area]
        // setTimeout( () => this.map_ref.current.leafletElement.flyToBounds(area_bounds, {duration:2, maxZoom:13}), 400)
        // setTimeout( () => this.zoom_to_cover_ports(this.port_ids), 400)

      }
      else {
        console.log('this isnt the first time summary was loaded')
        this.findAndUpdateSelectedDayIndex(this.state.selectedDay);
        this.onSliderUpdate(this.state.values); // turns out this is actually necessary
        this.query_acquisition(this.state.selectedDay, this.state.product_type)
      }
      // console.log('all_data',data)
      // console.log('i will '+(IS_DEV?'always love':'find you and kill')+' you...')
      //end mergeJsonResponses
    }
    // var unavailablePorts = []
    // var availablePorts = []
    // for(var i = 0; i < port_ids.length; i++){
    //   if(!implementedPorts.includes(port_ids[i])){
    //     unavailablePorts.push(portNameDict[port_ids[i]])
    //   }
    //   else{
    //     availablePorts.push(portNameDict[port_ids[i]])
    //   }
    // }
    // alert("port_ids: " + port_ids + ", availablePorts: " + availablePorts + ", unavailablePorts: " + unavailablePorts)
    // if(unavailablePorts.length > 0){
    //   this.setState({showInformationMessage: true, unavailablePorts: unavailablePorts, availablePorts: availablePorts})
    // }

    // this.state.all_data = {}
    if(min_areas) {
      this.setState({areas: min_areas})
    }
    else {
      min_areas = this.state.areas
    }
    this.set_cursor_waititing(true)
    // console.log('fetching summary for areas: ', min_areas)
    Promise.all(min_areas.map(area => {

        return fetch(API_ADDRESS + '/' + area + '/summary'+ avg_mode_extension(this.state.averaging_mode) +'.json', 
        {
          headers: {
            'Accept': 'application/json',
          },
          method: 'GET',
        })
        .then((response) =>{
          if (response.status !== 200) {
            this.setState({error:response.status})
            console.log("non 200 OK response in getSummary()->fetch()", response)
          }
          else {
            return response;
          } 
        })
        .then(response => response.json())
        .then(handleJsonResponse)
        .catch(err => console.log('Caught error in summary response.json',err))
      })
    ).then( responses => mergeJsonResponses(responses) )
    .then( () => {this.set_cursor_waititing(false)})
  }

  query_acquisition = async (day, product_type) => {
    // console.log('query_acquisition', day, product_type)
	  const acquisition_datetime_str = acquisition_datetime_formatter(day)
    const handleJsonResponse = (response, delete_area) => {
      // console.log('handling json response for query_acquisition:', day, product_type, response)
      let new_data = this.state.geodata
      if(response){
        new_data[response.city] = response
        this.setState({product_description:response.description + '\n'})
      }
      if(delete_area){
        delete new_data[delete_area]
      }
      let cumData = []
      let newMax = -Infinity
      Object.keys(new_data).forEach( (cityname, index) => {
        let citydata = new_data[cityname]
        let internallyReshaped = citydata['data'].map( (elem, index) => { return {lat:elem[0], lng:elem[1], value:elem[2]} })
        cumData = [ ...cumData, ...internallyReshaped]
        if(citydata['max'] > newMax){
          newMax = citydata['max']
        }
       })
      // console.log('Max concentration of data from',Object.keys(new_data),'after',response,'is',newMax)
      const reshapedData = { max: HEATMAP_MAX, data: cumData, product_type: product_type, date: day, cities:Object.keys(new_data) }
      this.setState({geodata: new_data})
      setTimeout(() => this.set_heatmap_data(reshapedData), 0)
      // this.setState({geodata: [response.data]})
    }

    // console.log('fetching data for', this.state.areas, product_type, acquisition_datetime_str);
    this.state.areas.map(area => {
        let request_address = API_ADDRESS + '/' + area + '/' + product_type + '/' + acquisition_datetime_str + '/' + (area + avg_mode_extension(this.state.averaging_mode) +'.json')
        // console.log('request_address', request_address)
        return fetch(request_address, 
          {
            headers: {
              'Accept': 'application/json',
            },
            method: 'GET',
          }
        )
        .then((response) =>{
          if (response.status !== 200) {
            console.log("non 200 OK response in query_acquisition()->fetch()", response)
            this.setState({error:response.status})
          }
          else {
            return response;
          } 
        })
        .then(response => response.json())
        .then(response => handleJsonResponse(response, null))
        .then(response => this.findAndUpdateSelectedDayIndex(safeCopyDate(day)))
        .catch(err => { 
          console.log('Caught error in query_acquisition for', area, day, err)
          handleJsonResponse(null, area)
          this.setState({error:err, selectedDay: safeCopyDate(day), selectedDayIndex: -1})
        })

    })
  }

  appKeyUpHandler = (event) => {
    // console.log("appKeyUpHandler", event)
    if(event.code === 'NopeArrowLeft' ||
        event.code === 'PageDown'
       ){
      this.onPrevClick(event);
    }
    else if (event.code === 'NopeArrowRight'||
        event.code === 'PageUp'
    ) {
      this.onNextClick(event);
    }
    if(event.code === 'Tab'){
      this.setState({showInformationMessage:!this.state.showInformationMessage});
    }
    if(event.code === 'KeyE'){
      const basic_mode = this.state.basic_mode
      if(basic_mode===2){
        this.setState({basic_mode:1})
      }
      else{
        this.setState({basic_mode:2})
      }
    }
    if(event.code === 'KeyX'){
      const basic_mode = this.state.basic_mode
      if(basic_mode===1){
        this.setState({basic_mode:0})
      }
      else{
        this.setState({basic_mode:2})
      }
    }
    if(event.code === 'Space'){
      this.swap_years(event)
    }
    // if(event.code === 'ArrowUp'){
    //   this.setState({zoom:this.state.zoom+1});
    // }
    // else if (event.code === 'ArrowDown') {
    //   this.setState({zoom:this.state.zoom-1});
    // }
  }

  onNextClick = (event) => {
    const current_day = this.state.selectedDay
    const all_dates = this.state.measurement_dates[this.state.product_type]
    if(!all_dates)
      return
    var after = all_dates.filter(date => { return date > current_day})
    if (after.length > 0){
      this.handleDayChange( after[0] )
    }
  }

  onPrevClick = (event) => {
    const current_day = this.state.selectedDay
    const all_dates = this.state.measurement_dates[this.state.product_type]
    if(!all_dates)
      return
    var after = all_dates.filter(date => { return date < current_day})
    if (after.length > 0){
      this.handleDayChange( after[after.length-1] )
    }
  }

  onLatestClick = (event) => {
    const all_dates = this.state.measurement_dates[this.state.product_type]
    if(!all_dates)
      return
    this.handleDayChange( all_dates[all_dates.length-1] )
  }

  onAllClick = (event) => {
    const all_dates = this.state.measurement_dates[this.state.product_type]
    if(!all_dates)
      return
    const begin = all_dates[0]
    const end = new Date(2020, 11, 31, 23, 59, 59)
    this.setState({ values:[begin, end] });
  }

  on2020Click = (event) => {
    const all_dates = this.state.measurement_dates[this.state.product_type]
    if(!all_dates)
      return
    const begin = all_dates[0]
    const end = safeCopyDate(all_dates[all_dates.length-1])
    end.setFullYear(2019)
    this.setState({ values:[begin, end] });
  }

  onYearClick = (event) => {
    const end = new Date()
    var begin = new Date()
    begin.setFullYear(end.getFullYear()-1)
    // begin.setDate(1)
    // begin.setMonth(0)
    this.setState({ values:[begin, end] });
    // console.log('This Year: ' , begin , end)
  }

  /* on2YearClick = (event) => {
    const end = new Date()
    var begin = new Date()
    begin.setDate(1)
    begin.setMonth(0)
    begin.setFullYear(begin.getFullYear()-1)
    this.setState({ values:[begin, end] });
    // console.log('This Year: ' , begin , end)
  } */

  onQuarterClick = (event) => {
    const end = new Date()
    var begin = new Date()
    begin.setMonth(end.getMonth()-3)
    // begin.setMonth(3*Math.floor(begin.getMonth()/3)-1)
    // begin.setDate(1)
    this.setState({ values:[begin, end] });
    // console.log('This Quarter: ' , begin , end)
  }

  /* onMonthClick = (event) => {
    const end = new Date()
    var begin = new Date()
    begin.setDate(1)
    this.setState({ values:[begin, end] });
    // console.log('This Month: ' , begin , end)
  } */

  findAndUpdateSelectedDayIndex = (day) => {
    // console.log('findAndUpdateSelectedDayIndex', day)
    const all_dates = this.state.measurement_dates[this.state.product_type]
  	const acquisition_datetime_str = acquisition_datetime_formatter(day)
  	// return this.state.selectedDay.index;
    // console.log('comparing', day, 'with', all_dates)
    let selectedDay = undefined
    let selectedDayIndex = undefined
    for(var i=0; i<all_dates.length; i++)
    // for(var i=all_dates.length-1; i>=0; i--)
    {
      let date_only =  acquisition_datetime_formatter(all_dates[i])
      if (all_dates[i] < day ) 
      {
        selectedDay = all_dates[i]
        selectedDayIndex = i
      }
      if (date_only === acquisition_datetime_str) 
      {
  	    // console.log('findAndUpdateSelectedDayIndex: selectedDay', all_dates[i])
        selectedDay = all_dates[i]
        selectedDayIndex = i
        this.setState({ selectedDay: safeCopyDate(selectedDay), selectedDayIndex:selectedDayIndex });
        return true
    	}
    	else{
    		// console.log(all_dates[i],'is NOT equal to', day)
    	}
    }
    console.log('couldnt find and updated selectedDay')
    if(selectedDay){
  	 this.setState({ selectedDay: safeCopyDate(selectedDay), selectedDayIndex:selectedDayIndex });
    }
    return false
  }


  handleDayChange = (day) => {
    if( acquisition_datetime_formatter(day)=== acquisition_datetime_formatter(this.state.selectedDay)){
      // console.log("returning immediately because selectedDay not changed")
      if(this.state.selectedDay.index && this.state.selectedDay.product_type) // only return if this is not a naive date obje
        return;
    }
    else{
      // console.log('new day', day)
      // console.log('selectedDay', this.state.selectedDay)
    }
    const all_dates = this.state.measurement_dates[this.state.product_type]
    if(!all_dates)
      return
  	const acquisition_datetime_str = acquisition_datetime_formatter(day)

    for(var i=all_dates.length-1; i>=0; i--)
    {
      const date_only =  acquisition_datetime_formatter(all_dates[i])
      if (date_only === acquisition_datetime_str) 
      {
    		// console.log(day,'as',acquisition_datetime_str,'is included')
  	  	this.query_acquisition( safeCopyDate(all_dates[i]), this.state.product_type)
  	  	this.setState({ selectedDay: safeCopyDate(all_dates[i]), selectedDayIndex:i });
  	    // console.log('selectedDay', i, all_dates[i])
        return true;
    	}
    	else{
    		// console.log(all_dates[i],'is NOT equal to', day)
    	}
    }
    return false
  }
	
  handleBarClick = ({ event, data, datum, color, index }) => {
    this.bar_clicked = true
    this.handleDayChange(getDateFromDatum(datum))
    // console.log('clicked bar', event, data, datum, color, index);
  }

  onSliderUpdate = values => {
    // console.log('onSliderUpdate')
    const hist_data = this.state.all_data
    if(Object.keys(hist_data).length===0)
      return
    const slider_size = this.state.values[1]-this.state.values[0]
    // console.log('slider_size', slider_size)
    var scaler = slider_size/7000000000/2
    // console.log('scaler', scaler)
    scaler = scaler<1 ? scaler=0 : scaler<3 ? scaler=1 : scaler<5 ? scaler=2 : scaler=4 
    // console.log('scaler', scaler)
    scaler = 0
    var new_hist_data = {}
    const sliderStart = new Date(values[0])
    const sliderEnd = new Date(values[1])
    // console.log('slider vals', sliderStart, sliderEnd)
    Object.keys(hist_data).forEach( product_type => {
      new_hist_data[product_type] = scaleBinnedData(hist_data[product_type], scaler)
      new_hist_data[product_type] = new_hist_data[product_type].filter(datum => { return isDatumInsideSliderRange(datum, sliderStart, sliderEnd) })
    })
    // console.log('filtered histogram_data after slider update', new_hist_data)
    if (implementedEmissionTypes.some( product_type => new_hist_data[product_type].length > 0) ){
      this.setState({ values:values, histogram_data:new_hist_data, histogram_scaler:scaler,})
    }
    else {
      this.setState({ histogram_scaler:scaler,})
    }

  }

  handlePortChange = (event) => {
	// this.setState({port_ids: [event]})
	// this.getSummary([event])
  console.log('handlePortChange', event)
  window.history.pushState( this.state.areas, 'SkyBase '+event, event )
    let port_bounds = this.cities[event].pad(-0.10)
    // this.map_ref.current.leafletElement.fitBounds(port_bounds)
    if(this.heatmapLayer && !arraysEqual(this.state.areas, [event])){
      this.heatmapLayer.setData({max:0, data:[], cities:[], date: undefined, product_type: undefined});
    }
    this.map_ref.current.leafletElement.flyToBounds(port_bounds)
  };

  onMoveEnd = (event) => {
    // console.log("onMoveEnd", event);
    // this.setState({
    //                 centerLat:event.target.getCenter().lat,
    //                 centerLon:event.target.getCenter().lng,
    //                 zoom:event.target.getZoom(),
    //               })

    var min_areas = []
    var map_bounds = this.map_ref.current.leafletElement.getBounds().pad(0.00)
    // console.log("map_bounds", map_bounds)
    Object.keys(this.cities).forEach( city => {
      // console.log("city", city)
      let city_bounds = this.cities[city].pad(0.05)
      let viewportInPort = city_bounds.overlaps(map_bounds)
      // console.log("viewportInPort", viewportInPort)
      if(viewportInPort) {
        min_areas.push(city)
        // console.log('viewportInPort', city)
        return;
      }
    })

    if(this.state.zoom >= MIN_PORT_CHANGE_ZOOM && min_areas.length>0 && !arraysEqual(this.state.areas, min_areas)){
      console.log('arrays NOT equal','min_areas', min_areas, 'areas', this.state.areas)
      // this.setState({areas: min_areas})
      // this.getSummary(min_areas)
      window.history.pushState( this.state.areas, 'SkyBase '+min_areas.join(','), min_areas.join(',') )
      setTimeout(() => this.getSummary(min_areas), 0)
      
    } 
    else{
      // console.log('arrays ARE equal','min_areas', min_areas, 'areas', this.state.areas)
      // console.log('OR', this.state.zoom, '>=?', MIN_PORT_CHANGE_ZOOM)
      // console.log('OR', min_areas.length,'>',0)

    }
  };

  onMoveStart = (event) => {
  }

  handleMapClick = (e) => {
    console.log("clickPos",e.latlng,"zoom",this.state.zoom)
    if(!this.state.basic_mode){
      console.log('this.state', this.state)
    }
    this.setState({ clickPos: e.latlng });
  }

  handleHistTypeChange = (event) => {
    console.log('handleHistTypeChange')
    this.setState({product_type: event})
    this.query_acquisition(this.state.selectedDay, event)
  } 

  handleAvgModeChange = (event) => {
    console.log('handleAvgModeChange')
    this.setState({averaging_mode: event})
    setTimeout(() => this.getSummary(), 0)
    // this.query_acquisition(this.state.selectedDay, this.state.product_type)
  }

  handleSummaryTypeChange = (event) => {
    console.log('handleSummaryTypeChange')
    this.setState({summary_type: event})
    this.getSummary()
  }

  handleColormapChange = (event) => {
    console.log('handleColormapChange', event)
    this.state.colormap = event
    this.query_acquisition(this.state.selectedDay, this.state.product_type)
  }

  swap_years = (event) => {
    console.log('swap_years', this.state.selectedDay)
    const curYear = this.state.selectedDay
    let otherYear = new Date(curYear.getTime())
    otherYear.setFullYear(2020-(this.state.selectedDay.getFullYear()%2019))
    this.findAndUpdateSelectedDayIndex(otherYear)
    this.query_acquisition(otherYear, this.state.product_type)
    // // code block to find nearest available date
    // const all_dates = this.state.measurement_dates[this.state.product_type]
    // if(!all_dates || all_dates.length === 0)
    //   return
    // let nearestDate = undefined
    // for(var i=0; i<all_dates.length; i++)
    // {
    //   if (all_dates[i] < otherYear || datesEqual(all_dates[i], otherYear)) 
    //   {
    //     nearestDate = all_dates[i]
    //     // console.log(all_dates[i], 'earlier or equal', otherYear)
    //   }
    //   else{
    //     // console.log(all_dates[i], 'later', otherYear)
    //   }
    // }
    // console.log('nearestDate', nearestDate)
    // if(nearestDate){
    //   this.handleDayChange(nearestDate)
    // }
  }

  render() {
    return (
      <Container className={this.state.wait?"wait":""} fluid={true}>
        <Row className="darkrow" noGutters={true}>
        	<Col md={12} lg={12} xl={12}>
              <div>
                <CookieConsent
                  location="bottom"
                  buttonText="Okay"
                  cookieName="skybase-user-has-accepted-cookies" 
                  style={{ background: "#2B373B", opacity:'80%', fontSize: 13 }}
                  buttonStyle={{ color: "#4e503b", fontSize: "13px" }}
                >
                  This website uses cookies to enhance the user experience and for analytics purposes.{" "}
                  <span style={{ fontSize: "10px" }}>
                    <a href="https://novit.ai" target="_blank" rel="noopener noreferrer">Novit.AI</a>
                  </span>
                </CookieConsent>
              </div>
	            <AlertDismissible />
	            <ModalDismissible />
              {this.render_productInfoMessage()}
              <div className="mygallery">
	    			    {this.render_map()}
	            </div>
              <div className="presets">
              	{this.state.all_data && this.render_presets()}
              </div>
	            <Row noGutters={true} className="histoslider">
                  {true && this.state.all_data &&  this.render_slider()}
		              {this.state.histogram_data &&  this.render_histogram()}
	            </Row>
            <div className="signout">
              <div className="">
                <Button
                  style={{margin:5, fontSize:10}}
                  variant="secondary"
                  disabled={false}
                  onClick={ (event) => { this.setState({showInformationMessage:true}) } }>
                  <FaInfo className="signouticon" /><div className="signouttext">{ this.state.product_description }</div>
                </Button>
              </div>
            </div>
              <div className="feedback">
              <div className="">
                <Button
                  style={{margin:5, fontSize:10}}
                  variant="info"
                  disabled={false}
                  onClick={ (event) => window.open('https://novit.ai/#contact','_blank') }>
                  <FaCommentDots className="feedbackicon" /><div className="feedbacktext"><span className="contact">{' '+('Contact at')+' '} </span><span className="feedbackurl">{'https://novit.ai'}</span>{' '}</div>
                </Button>
              </div>
            </div>
            <div className="adsholder">
                <div className="adsblock">
                    <span style={{display:'None'}}> ads here ? </span>
                      {/*<AdSense.Google
                      client='pub-4929496559240539'
                      slot='7806394673'
                      style={{ width: 320, height: 50 }}
                      format='auto'
                      responsive='true'
                    />*/}
                </div>
            </div>
            <div className="novitholder" style={{opacity:'65%'}}>
                <div className="novitblock">
                  <a href="https://novit.ai" target="_blank" rel="noopener noreferrer">
                    <Image className="" src='./novit_textlogo_H250px_whiteBg.jpg' alt='Novit.AI Logo' fluid/>
                  </a>
                </div>
            </div>
        	</Col>
        </Row>
      </Container>
    );
  }


  render_presets() {
    const should_center = this.state.width < 1100;
    const {
      state: { measurement_dates, product_type, basic_mode, averaging_mode, summary_type, colormap, show_dense, selectedDay },
    } = this
    let cities_in_view = Object.keys(this.cities).sort().filter( city =>  this.cities[city].pad(0.05).overlaps(this.map_ref.current.leafletElement.getBounds()))
  	return (
  		<Row noGutters={true}>
  			<Col xs={12} sm={12} md={3} lg={3} style={should_center ? {textAlign: 'center'}:{}}>
          <div className="presetbuttonsdiv btn-group">
            <Button
              style={{margin:3, marginTop:8}}
              variant="secondary"
              disabled={false}
              onClick={ this.onAllClick }>
              <FaRegCalendarAlt />{ ' Show all available dates' }
            </Button>
            <Button
              style={{margin:3, marginTop:8}}
              variant="secondary"
              disabled={false}
              onClick={ this.on2020Click }>
              { ' Show all 2020' }
            </Button>
            {/*<Button
              style={{margin:3, marginTop:8}}
              variant="secondary"
              disabled={false}
              onClick={ this.onYearClick }>
              { ' Last 12 Months ' }
            </Button>*/}
            {/*<Button
              style={{margin:3, marginTop:8}}
              variant="secondary"
              disabled={false}
              onClick={ this.onQuarterClick }>
              { ' Last 3 Months ' }
            </Button>*/}
            {/*<Button
              style={{margin:3, marginTop:8}}
              variant="secondary"
              disabled={false}
              onClick={ this.onMonthClick }>
              { ' This Month' }
            </Button>*/}
           </div>
	        </Col>
          <Col xs={12} sm={12} md={!basic_mode?5:4} lg={!basic_mode?5:4} className="mx-auto" style={{textAlign: 'center'}}>
            <div className="mx-auto plotbuttonsdiv btn-group">
              {!basic_mode && <Dropdown>
                <Dropdown.Toggle className="expertdropdownbutton"
                                variant="light" 
                  >
                  <span>
                    <FaList className="histtypebuttonicon"/>
                    <span className="plotbuttontext" style={should_center?{fontSize:10}:{}}>{averaging_mode}</span>
                  </span>
                </Dropdown.Toggle>
                <Dropdown.Menu>
                  {implementedAveragingModes && implementedAveragingModes.map( (key, index) => 
                    { 
                      return <Dropdown.Item key={key} eventKey={key} onSelect={ () => this.handleAvgModeChange(key)}> {key}</Dropdown.Item>
                    }
                  )}
                </Dropdown.Menu>
              </Dropdown>}
              {/*<Dropdown>
                <Dropdown.Toggle className="expertdropdownbutton"
                                variant="light" 
                  >
                  <span>
                    <FaList className="histtypebuttonicon"/>
                    <span className="plotbuttontext">{product_type}</span>
                  </span>
                </Dropdown.Toggle>
                <Dropdown.Menu>
                  {implementedEmissionTypes && implementedEmissionTypes.map( (key, index) => 
                    { 
                      return <Dropdown.Item key={key} eventKey={key} onSelect={ () => this.handleHistTypeChange(key)}> {key}</Dropdown.Item>
                    }
                  )}
                </Dropdown.Menu>
              </Dropdown>*/}
              {!basic_mode && <Dropdown>
                <Dropdown.Toggle className="expertdropdownbutton"
                                variant="light" 
                  >
                  <span>
                    <FaList className="histtypebuttonicon"/>
                    <span className="plotbuttontext" style={should_center?{fontSize:10}:{}}>{fixCase(summary_type)}</span>
                  </span>
                </Dropdown.Toggle>
                <Dropdown.Menu>
                  {dataSummaryTypes && dataSummaryTypes.map( (key, index) => 
                    { 
                      return <Dropdown.Item key={key} eventKey={key} onSelect={ () => this.handleSummaryTypeChange(key)}> {fixCase(key)}</Dropdown.Item>
                    }
                  )}
                </Dropdown.Menu>
              </Dropdown>}
              {!basic_mode && <Dropdown>
                <Dropdown.Toggle className="expertdropdownbutton"
                                variant="light" 
                  >
                  <span>
                    <FaList className="histtypebuttonicon"/>
                    <span className="plotbuttontext" style={should_center?{fontSize:10}:{}}>{fixCase(colormap)}</span>
                  </span>
                </Dropdown.Toggle>
                <Dropdown.Menu>
                  {Object.keys(COLORMAPS).map( (key, index) => 
                    { 
                      return <Dropdown.Item key={key} eventKey={key} onSelect={ () => this.handleColormapChange(key)}> {fixCase(key)}</Dropdown.Item>
                    }
                  )}
                </Dropdown.Menu>
              </Dropdown>}
              {!basic_mode && <Button className="plotbutton"
                onClick={(event)=>this.setState({show_dense:!show_dense})}
                variant="light">
                <span>
                  <FaChartLine className="histplotbuttonicon"/>  
                  <span className="plotbuttontext" style={should_center?{fontSize:10}:{}}>Line Plot</span> 
                  <input style={{margin:3, float:"right"}} 
                      name="Dense Plot Enabled"
                      type="checkbox"
                      checked={show_dense}
                      onChange={(event)=>this.setState({show_dense:!show_dense})} />
                </span>
              </Button>}
            </div>
          </Col>
          <Col xs={12} sm={12} md={4} lg={4} className={should_center?'':'align-self-start'} style={should_center?{textAlign: 'center'}:{textAlign: 'right'}}>
            <div className={should_center?'mx-auto':'ml-auto'}>
              <Row noGutters={true} className="ml-auto" >
                <Col xs={0} sm={0} md={0} lg={0} className="ml-auto">
                </Col>
                <Col xs={4} sm={4} md={4} lg={4} className="ml-auto">
                <div className="nextprevyearbutton">
                  <Button className=""
                    onClick={(event)=>this.swap_years(event)}
                    variant="secondary"
                    >
                    <span>
                      <span className="plotbuttontext">{selectedDay.getFullYear()%2019 == 0? 'Show next year': 'Show previous year'}</span>
                    </span>
                  </Button>   
                </div>
                </Col>

                <Col xs={4} sm={4} md={4} lg={3} className="auto">
                <div className="datepickerholder">
                  <DatePicker  
                    todayButton="Today" 
                    selected={selectedDay} 
                    onChange={date => this.handleDayChange(date)} 
                    showMonthDropdown
                    showYearDropdown
                    dropdownMode="select"
                    maxDate={(measurement_dates[product_type].slice(-1)[0])}
                    minDate={(measurement_dates[product_type][0])}
                    dateFormat="dd-MMM-yyyy"
                    popperClassName="popper-class"
                    popperPlacement="bottom"
                    withPortal={should_center}
                    className={"datepicker-class "+("datepicker-class-"+selectedDay.getFullYear())}
                    />
                </div>
                </Col>

                <Col xs={4} sm={4} md={4} lg={5} className="mr-auto">
                <div className="cityselector">
                  <SelectSearch options={Object.keys(this.cities).sort().map(city=>({name: fixCase(city), value:city}))}
                                defaultValue={initial_area}
                                placeholder={"Region Select"} 
                                onChange={this.handlePortChange}
                                search
                                autoComplete
                                closeOnSelect
                                value={cities_in_view}
                                />
                  {false && <DropdownButton style={{fontSize:10, right:0, paddingRight:0, marginTop:8, maxWidth:120}} drop='up' id="dropdown-basic-button" 
                              title={'Region Select '} 
                              onSelect={this.handlePortChange}
                              className="ml-auto"
                              >
                        {this.cities && Object.keys(this.cities).sort().map( city =>  (
                          this.cities[city].pad(0.05).overlaps(this.map_ref.current.leafletElement.getBounds().pad(0.00)) ? (
                              <Dropdown.Item style={{backgroundColor:"#8dc7f0"}} key={city} eventKey={city} >{fixCase(city)}</Dropdown.Item>
                            )
                            :(
                              <Dropdown.Item style={{backgroundColor:"#fff"}} key={city} eventKey={city} >{fixCase(city)}</Dropdown.Item>
                            )
                            ))}
                  </DropdownButton> }
                </div>
                </Col>
              </Row>
            </div>
          </Col>
  		</Row>
  		)
  }

  render_slider() {
    const {
      state: { domain, values },
    } = this
    return (
        <div  className="slider">
          <Slider
          mode={1}
          step={1000*60*60*24}
          domain={domain}
          rootStyle={sliderStyle}
          onUpdate={this.onSliderUpdate}
          values={values}
          >
          <Rail>
            {({ getRailProps }) => <SliderRail getRailProps={getRailProps} />}
          </Rail>
          <Handles>
            {({ handles, getHandleProps }) => (
              <div className="slider-handles">
                {handles.map(handle => (
                  <Handle
                    key={handle.id}
                    handle={handle}
                    domain={domain}
                    getHandleProps={getHandleProps}
                  />
                ))}
              </div>
            )}
          </Handles>
          <Tracks left={false} right={false}>
            {({ tracks, getTrackProps }) => (
              <div className="slider-tracks">
                {tracks.map(({ id, source, target }) => (
                  <Track
                    key={id}
                    source={source}
                    target={target}
                    getTrackProps={getTrackProps}
                  />
                ))}
              </div>
            )}
          </Tracks>
          <Ticks count={5}>
            {({ ticks }) => (
              <div className="slider-ticks">
                {ticks.map(tick => (
                  <Tick key={tick.id} tick={tick} count={ticks.length} format={yearless_human_datetime_formatter}/>
                ))}
              </div>
            )}
          </Ticks>
        </Slider>
        </div>
        )
  }

  render_histogram() {
    const {
      state: { product_type, histogram_data, measurement_dates, selectedDayIndex,
              all_data, values, histogram_scaler, areas, show_dense, geodata, width },
    } = this

    if(histogram_data === undefined
      || all_data === undefined
      // || selectedDayIndex === undefined
      || measurement_dates === undefined
      || measurement_dates[product_type] === undefined
       )
      return null;



    const product_data = histogram_data[product_type]
    if(!product_data || product_data.length===0)
      return

    let data_by_year = {}
    let deepcopied_product_data = scaleBinnedData(product_data, histogram_scaler)
    // console.log('deepcopied_product_data', deepcopied_product_data)
    for (let i=0; i<deepcopied_product_data.length; i++){
      let datum_date_dt = parseDate(deepcopied_product_data[i].date_str)
      let datum_year = datum_date_dt.getFullYear().toString()
      if(data_by_year[datum_year] === undefined){
        data_by_year[datum_year] = []
      }
      modifyDatumYear(deepcopied_product_data[i])
      deepcopied_product_data[i].id = 'copied|'+deepcopied_product_data[i].id
      data_by_year[datum_year].push(deepcopied_product_data[i])
    }

    // console.log('histogram_data', histogram_data)
    // console.log("selectedDayIndex",selectedDayIndex)
    var selectedDayDatum = null;
    // console.log("measurement_dates",measurement_dates)
    let selectedDay = measurement_dates[product_type][selectedDayIndex]
    // console.log("selectedDay", selectedDay)
    if (selectedDay !== undefined) {
      selectedDayDatum = {...all_data[product_type][selectedDay.index]}
      var copied_selectedDay = scaleBinnedData([selectedDayDatum], histogram_scaler)[0]
      modifyDatumYear(copied_selectedDay)
      copied_selectedDay.id = 'selectedDay'+'|'+copied_selectedDay.id
    }
    // console.log("selectedDayDatum",selectedDayDatum)
    // console.log("copied_selectedDay",copied_selectedDay)
    // console.log('product_data before render', product_data.length, product_data)
    // console.log('data_by_year', data_by_year)
    // console.log('state.geodata', geodata)
    return (
        <div  className="histogram">
            {[2019, 2020].map( (year,index) => 
                  <div key={year} className="legend" style={{right:30+(year===2020?70:0), borderColor:HIST_COLORS[year]}}>
                    <span style={{color:HIST_COLORS[year]}}>
                      <FaChartLine style={{color:HIST_COLORS[year]}} className="histplotbuttonicon" />  
                      <span className="plotbuttontext"> {year}</span> 
                    </span>
                  </div>
              )
            }
            <ResponsiveHistogram
            	margin={{bottom:24, top:32}}
                height={161}
                ariaLabel="Histogram of Data"
                orientation="vertical"
                cumulative={false}
                normalized={false}
                valueAccessor={datum => datum}
                binType="numeric"
                renderTooltip={({ event, datum, data, color }) => (
                  <div>
                    <strong style={{ color }}>{human_datetime_formatter(getDateFromDatum(datum))}</strong>
                    <div><strong>{areas.map(fixCase).join()}</strong></div>
                    <div><strong>{datum.count===ZERO_DATA_DAY_HEIGHT ? 0 : datum.count.toFixed(3)} {'m'+UNITS[product_type]}</strong></div>
                  </div>
                )}
             >
                {Object.keys(data_by_year).slice(0).reverse().map((year, index) => {  
                    if(data_by_year[year] && data_by_year[year].length>0)
                    return (
                        <BarSeries
                          key={'bar'+'-'+year}
                          animated={false}
                          fill={HIST_COLORS[year]}
                          fillOpacity={0.5}
                          stroke='#f0f0f00f'
                          strokeOpacity={0.2}
                          binnedData = {data_by_year[year]}
                          onClick={this.handleBarClick}
                        />
                      )
                    }
                  )
                }
                {Object.keys(data_by_year).slice(0).reverse().map((year, index) => {  
                    if(data_by_year[year] && data_by_year[year].length>0)
                    return (
                      <DensitySeries
                        key={'dense'+'-'+year}
                        animated={false}
                        stroke={HIST_COLORS[year]}
                        fill={HIST_COLORS[year]}
                        showLine={show_dense}
                        showArea={show_dense}
                        binnedData = {data_by_year[year]}
                        smoothing={0.0001}
                        kernel='gaussian'
                      />
                      )
                    }
                  )
                }
                {/* Selected day data bar */}
                {selectedDayDatum && 
                  isDatumInsideSliderRange(selectedDayDatum, new Date(values[0]), new Date(values[1])) &&
                  <BarSeries
                    key={'selectedDayBar'}
                    animated={true}
                    fill='black'
                    stroke='#8EDC2B'
                    fillOpacity={0.7}
                    binnedData = {(copied_selectedDay.count !== 0 ?  [copied_selectedDay] 
                                                                         : [ 
                                                                              { bin0:copied_selectedDay.bin0, 
                                                                                bin1:copied_selectedDay.bin1, 
                                                                                count:ZERO_DATA_DAY_HEIGHT, 
                                                                                id:'selectedDayZero|'+copied_selectedDay.id,
                                                                                product_type:copied_selectedDay.product_type,
                                                                                date_str:copied_selectedDay.date_str,
                                                                                city:copied_selectedDay.city,
                                                                              } 
                                                                            ]) 
                                  }
                    onClick={this.handleBarClick}
                  />
                }

                <YAxis 
                  label={'m'+UNITS[product_type]} 
                />
                <XAxis 
                  numTicks={Math.round(width/125)}
                  tickFormat={(tick, tickIndex) => yearless_human_datetime_formatter(new Date(tick))}
                />
                </ResponsiveHistogram>
            </div>
        )
  }

  set_geojson_feature_style(feature) {
    return {
      fillColor: feature.properties['fill'],
      fillOpacity: feature.properties['fill-opacity'],
      color: feature.properties['stroke'],
      opacity: feature.properties['stroke-opacity'],
      weight: feature.properties['stroke-width'],
    };
  }

  append_popup_to_contour(feature, layer) {
    return layer.bindTooltip((layer) => {
          return layer.feature.properties['title']; 
      }, {sticky:true})
  }

  set_heatmap_data = (reshapedData) => {
    const {
      state: { zoom, averaging_mode, product_type, colormap },
    } = this
    // console.log('reshapedData before render map', reshapedData)
    if(reshapedData && this.map_ref.current && this.map_ref.current.leafletElement)
    {
      const map_pixel_bounds = this.map_ref.current.leafletElement.getPixelBounds()
      const map_height_px = map_pixel_bounds.max.y - map_pixel_bounds.min.y
      if( map_height_px>20 && zoom > MIN_PORT_CHANGE_ZOOM && this.map_ref.current && reshapedData.data.length>0)
      {
          // console.log('creating heatmap')
          var cfg = {
            // radius should be small ONLY if scaleRadius is true (or small radius is intended)
            "radius": RADIUS[averaging_mode][product_type],
            "maxOpacity": .85, 
            // scales the radius based on map zoom
            "scaleRadius": true, 
            // if set to false the heatmap uses the global maximum for colorization
            // if activated: uses the data maximum within the current map boundaries 
            //   (there will always be a red spot with useLocalExtremas true)
            "useLocalExtrema": false,
            // which field name in your data represents the latitude - default "lat"
            latField: 'lat',
            // which field name in your data represents the longitude - default "lng"
            lngField: 'lng',
            // which field name in your data represents the data value - default "value"
            valueField: 'value',
            
            gradient: COLORMAPS[colormap],
          };

          this.map_ref.current.container.focus();
          if(!this.heatmapLayer) {
            this.heatmapLayer = new HeatmapOverlay(cfg);
            this.heatmapLayer.addTo(this.map_ref.current.leafletElement);
          }
          // console.log('reshapedData for heatmap', reshapedData)
          // console.log('heatmapLayer', this.heatmapLayer)
          this.heatmapLayer._heatmap.configure(cfg)
          this.heatmapLayer.cfg.gradient = cfg.gradient
          this.heatmapLayer.setData(reshapedData);
          // console.log('after', this.heatmapLayer.cfg.gradient)
          this.map_ref.current.leafletElement.attributionControl.addAttribution("<a href='https://www.tropomi.eu/data-products/level-2-products' target='_blank'>Contains modified Copernicus Sentinel data 2020</a>");
      }
      else{
        console.log('either map is not ready yet or the data')
        if(this.heatmapLayer)
          this.heatmapLayer.setData({max:0, data:[], cities:[], date: undefined, product_type: undefined});
      }
    }
  }

  render_map(){
    const {
      state: { zoom, centerLat, centerLon, colormap, areas, wait, geodata },
    } = this

    const WrappedSearch = withLeaflet(ReactLeafletSearch)
    // var this.citiesKeys = Object.keys(this.cities);
    // var dist_list = []
    // const centerLat = centerLat
    // const centerLon = centerLon
    // for(var i = 0; i < this.citiesKeys.length; i++)
    // {
    //   let key = this.citiesKeys[i]
    //   let distance = Math.sqrt(Math.pow((centerLat - (this.cities[key][0][0]+this.cities[key][1][0])/2), 2) + Math.pow((centerLon - (this.cities[key][0][1]+this.cities[key][1][1])/2), 2))
    //   dist_list[i] = {'port_id':this.citiesKeys[i], 'dist': distance}
    // }
    // dist_list.sort((a, b) => (a.dist> b.dist) ? 1 : -1)

    var southWest = L.latLng(-89.98155760646617, -180);
    var northEast = L.latLng(89.99346179538875, 180);
    var bounds = L.latLngBounds(southWest, northEast);

    return (
      <div>
        <Map
          ref={this.map_ref}
          className="mapclass"
          onMoveEnd={this.onMoveEnd}
          onMoveStart={this.onMoveStart}
          zoom={zoom}
          center={[centerLat, centerLon]}
          onClick={this.handleMapClick}
          maxZoom={18}
          minZoom={4}
          keyboard={true}
          maxBounds={bounds}
          maxBoundsViscosity={1.0}
          // bounds={[
          //   [27.143063170960506, 50.31741485776232],
          //   [27.049456138571255, 50.2109285639828]

          // ]}
        >
        <div className="paletteholder">
          <div className="maxblock" style={{opacity:'100%'}}>
            <span> {1e3*HEATMAP_MAX}</span>
          </div>
          <div className="minblock" style={{opacity:'100%'}}>
            <span> 0.0</span>
          </div>
          <div className="unitblock" style={{opacity:'100%'}}>
            <span> m{UNITS[Object.keys(UNITS)[0]]}</span>
          </div>
          <div className="paletteblock" style={{background: colormap_to_gradient(colormap)}}>
          </div>
        </div>
        <WrappedSearch 
            position="topleft"
            provider="OpenStreetMap" 
            inputPlaceholder={":"+Math.round(centerLat*1e5)/1e5+", "+Math.round(centerLon*1e5)/1e5}
            search={[]} // Setting this to [lat, lng] gives initial search input to the component and map flies to that coordinates, its like search from props not from user
          />
        <TileLayer
              attribution='&copy; <a target="_blank" href="https://www.thunderforest.com/">ThunderForest</a>'
              url="https://tile.thunderforest.com/landscape/{z}/{x}/{y}.png?apikey=adeacfa97b3d4d739935ac3232476171"
            />
        {areas.map(area => {
          if(zoom > MIN_PORT_CHANGE_ZOOM && !geodata[area] && !wait && this.cities[area]){
            // console.log("city data for this day doesnt exist", this.state.selectedDay, area, JSON.stringify(this.cities[area]))
            return (
              <Rectangle
                    key={area}
                    bounds={this.cities[area]}
                    fillOpacity={0.3}
                    stroke={true}
                    color='gray'
                  >
                  <Tooltip permanent={false} sticky={true} zIndexOffset={2} className="labeltooltip">
                    <div>
                      <span className="norasterexists">No data exists for this day.</span>
                    </div>
                </Tooltip>
              </Rectangle>)}}) }
        </Map>
      </div>
    );
  }

  toggle_keyboard_shortcuts = () => {
    if(this.state.keyboard_shortcuts_enabled){
      document.removeEventListener('keyup', this.appKeyUpHandler); 
    }
    else{
      document.addEventListener('keyup', this.appKeyUpHandler);
    }
    this.setState({keyboard_shortcuts_enabled:!this.state.keyboard_shortcuts_enabled})
  }

  handleCloseMessage = () => {
    this.setState({showInformationMessage: false})
  }
  render_productInfoMessage() {
    const {
      state: { selectedDay, product_description, product_type, showInformationMessage, keyboard_shortcuts_enabled },
    } = this

    //const [show, setShow] = useState(unavailablePortChosen);

    // const handleClose = () => setShow(false);
    // const handleShow = () => setShow(true);
    const units = UNITS[product_type]
    const formatted_selectedDay = human_datetime_formatter(selectedDay)
    return (
        <Fragment>
          <Modal show={showInformationMessage} onHide={this.handleCloseMessage}>
            <Modal.Header closeButton>
              <Modal.Title> 
                <div className="novitcontainer">
                  <a href="https://novit.ai" target="_blank" rel="noopener noreferrer">
                    <Image className="" src='./novit_textlogo_H250px_whiteBg.jpg' alt='Novit.AI Logo' fluid/>
                  </a>
                </div>
              </Modal.Title>
            </Modal.Header>
            <Modal.Body>   
              <div>
                <strong> Reading Heatmaps </strong>
              </div>
              <div>
                Areas with high concentrations are specified with <u>brighter colours</u>, while areas with low concentrations are specified with <u>darker colours</u> and anything has <u>varying brightness</u> in the heatmap regardlesss of displayed colour. Also note that maximum intensity <u>(white)</u> depicts a concentrations of {HEATMAP_MAX} mol/m^2 or more, where almost transparent <u>gray</u> means 0.
              </div>
              <br/>
              <div>
                <strong> Data Processing </strong>
              </div>
              <div>
                <u>Raw:</u> Daily S5P data is shown as is.
              </div>
              <div>
                <u>Interpolated:</u> Raw data is interpolated onto a common grid, where some nonexistent data is extrapolated from existing data where possible.
              </div>
              <div>
                <u>Averaged:</u> A 10-day running average of interpolated data is taken where non-existent data in interpolated data is ignored.
              </div>
              <br/>
              <div>
                <strong> Product information </strong>
              </div>
              <div>
                {product_description}
              </div>
              <div>
                {formatted_selectedDay}
              </div>
              <div>
                Units: {units}
              </div>
              <br/>
              <div>
                <strong> Keyboard Shortcuts </strong> <Button variant="light" onClick={this.toggle_keyboard_shortcuts}><span>( Enabled <input type="checkbox" checked={keyboard_shortcuts_enabled} name="Enabled"/> )</span></Button>
              </div>
              <div>
                <u>J/K, PageUp/PageDown</u> for navigating dates
              </div>
              <div>
                <u>Up/Down/Left/Right</u> for panning the map
              </div>
              <div>
                <u>+/-</u> for changing zoom levels
              </div>
              <div>
                <u><i>Space bar</i></u> for swapping years between 2019 & 2020
              </div>
              <div>
                <u> i </u> for popping this window.
              </div>
              <br/>
              <small>
                <a href="https://www.tropomi.eu/data-products/level-2-products" target="_blank" rel="noopener noreferrer">
                  Contains modified Copernicus Sentinel data 2020.
                </a>
              </small>
            </Modal.Body>
            <Modal.Footer>
              <Button variant="primary" onClick={this.handleCloseMessage}>
                Thank you!
              </Button>
            </Modal.Footer>
          </Modal>
        </Fragment>

    );
  }


}

export default App;
