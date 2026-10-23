import { Client, makeClient } from "./client";
const util = require("./util");

export default class App extends Client {}

function start() { return makeClient(); }
