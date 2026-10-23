import axios from "axios";

export class Client {
  get(url: string) { return axios.get(url); }
}

export function makeClient() { return new Client(); }
